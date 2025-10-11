"""
Notification Service Health Check Utilities
===========================================

Independent health check functionality for Notification service.
No shared dependencies - completely self-contained.
"""

import asyncio
import time
from typing import Any, Callable, Dict

from sqlalchemy import text

from ..core.database import database_manager


class NotificationServiceHealthChecker:
    """Notification Service specific health checker"""

    def __init__(self, service_name: str = "notification_service") -> None:
        self.service_name = service_name
        self.checks: Dict[str, Callable[[], Any]] = {}
        self.start_time = time.time()

    def add_check(self, name: str, check_func: Callable[[], Any]) -> None:
        """Add a health check function"""
        self.checks[name] = check_func

    async def run_checks_async(self) -> Dict[str, Any]:
        """Run all health checks asynchronously"""
        results = {}
        check_start_time = time.time()

        for name, check_func in self.checks.items():
            individual_start = time.time()
            try:
                # Check if the function is a coroutine
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                result["duration_ms"] = round(
                    (time.time() - individual_start) * 1000, 2
                )
                results[name] = result
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e),
                    "duration_ms": round((time.time() - individual_start) * 1000, 2),
                }

        total_time = (time.time() - check_start_time) * 1000
        uptime = time.time() - self.start_time

        return {
            "service": self.service_name,
            "status": "healthy"
            if all(result.get("status") == "healthy" for result in results.values())  # type: ignore
            else "unhealthy",
            "checks": results,
            "total_duration_ms": round(total_time, 2),
            "uptime_seconds": round(uptime, 2),
            "timestamp": time.time(),
        }

    def add_notification_specific_checks(self) -> None:
        """Add Notification Service specific health checks"""

        def basic_check() -> Dict[str, Any]:
            return {
                "status": "healthy",
                "message": "Notification Service is running",
                "version": "1.0.0",
                "component": "core",
            }

        async def database_check() -> Dict[str, Any]:
            """Check database connectivity and basic operations"""
            try:
                async with database_manager.async_session_maker() as session:
                    # Test basic connectivity
                    await session.execute(text("SELECT 1"))

                    # Get notification statistics
                    result = await session.execute(
                        text("""
                        SELECT
                            COUNT(*) as total_notifications,
                            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_notifications,
                            COUNT(CASE WHEN status = 'sent' THEN 1 END) as sent_notifications,
                            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_notifications
                        FROM notifications
                    """)
                    )
                    stats = result.fetchone()

                    return {
                        "status": "healthy",
                        "message": "Database connection successful",
                        "component": "database",
                        "stats": {
                            "total_notifications": stats[0] if stats else 0,
                            "pending_notifications": stats[1] if stats else 0,
                            "sent_notifications": stats[2] if stats else 0,
                            "failed_notifications": stats[3] if stats else 0,
                        },
                    }
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "message": f"Database connection failed: {str(e)}",
                    "component": "database",
                    "error": str(e),
                }

        self.add_check("basic", basic_check)
        self.add_check("database", database_check)


async def create_notification_service_health_check_async(
    service_name: str = "notification_service", version: str = "1.0.0"
) -> Dict[str, Any]:
    """Create comprehensive Notification Service health check"""
    health_checker = NotificationServiceHealthChecker(service_name)
    health_checker.add_notification_specific_checks()
    return await health_checker.run_checks_async()
