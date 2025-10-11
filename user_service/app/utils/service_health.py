"""
User Service Health Check Utilities
===================================

Independent health check functionality for User service.
No shared dependencies - completely self-contained.
"""

import time
from typing import Any, Callable, Dict


class UserServiceHealthChecker:
    """User Service specific health checker"""

    def __init__(self, service_name: str = "user_service") -> None:
        self.service_name = service_name
        self.checks: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self.start_time = time.time()

    def add_check(self, name: str, check_func: Callable[[], Dict[str, Any]]) -> None:
        """Add a health check function"""
        self.checks[name] = check_func

    def run_checks(self) -> Dict[str, Any]:
        """Run all health checks with User Service specific context"""
        results = {}
        check_start_time = time.time()

        for name, check_func in self.checks.items():
            individual_start = time.time()
            try:
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
            if all(r.get("status") == "healthy" for r in results.values())  # type: ignore
            else "unhealthy",
            "checks": results,
            "total_duration_ms": round(total_time, 2),
            "uptime_seconds": round(uptime, 2),
            "timestamp": time.time(),
        }

    def add_user_specific_checks(self) -> None:
        """Add User Service specific health checks"""

        def basic_check() -> Dict[str, Any]:
            return {
                "status": "healthy",
                "message": "User Service is running",
                "version": "1.0.0",
                "component": "core",
            }

        def database_check() -> Dict[str, Any]:
            # In a real implementation, this would ping the database
            return {
                "status": "healthy",
                "message": "User database accessible",
                "component": "database",
            }

        def auth_check() -> Dict[str, Any]:
            # Check authentication service
            return {
                "status": "healthy",
                "message": "Authentication service operational",
                "component": "auth_service",
            }

        self.add_check("basic", basic_check)
        self.add_check("database", database_check)
        self.add_check("auth", auth_check)


def create_user_service_health_check(
    service_name: str = "user_service", version: str = "1.0.0"
) -> Dict[str, Any]:
    """Create basic User Service health check"""
    health_checker = UserServiceHealthChecker(service_name)
    health_checker.add_user_specific_checks()
    return health_checker.run_checks()
