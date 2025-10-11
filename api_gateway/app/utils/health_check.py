"""
API Gateway Health Check Utilities
======================================

Independent health check functionality for API Gateway service.
No shared dependencies - completely self-contained.
"""

import time
from typing import Any, Callable, Dict, Optional


class APIGatewayHealthChecker:
    """API Gateway specific health checker"""

    def __init__(self, service_name: str = "api_gateway") -> None:
        self.service_name = service_name
        self.checks: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self.start_time = time.time()
        self.service_registry = None

    def set_service_registry(self, service_registry: Any) -> None:
        """Set service registry for backend service health checks"""
        self.service_registry = service_registry

    def add_check(self, name: str, check_func: Callable[[], Dict[str, Any]]) -> None:
        """Add a health check function"""
        self.checks[name] = check_func

    def run_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results: Dict[str, Dict[str, Any]] = {}
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
            if all(r.get("status") == "healthy" for r in results.values())
            else "unhealthy",
            "checks": results,
            "total_duration_ms": round(total_time, 2),
            "uptime_seconds": round(uptime, 2),
            "timestamp": time.time(),
        }

    def add_basic_checks(self) -> None:
        """Add basic API Gateway health checks"""

        def basic_check() -> Dict[str, Any]:
            return {
                "status": "healthy",
                "message": "API Gateway is running",
                "version": "1.0.0",
            }

        def backend_services_check() -> Dict[str, Any]:
            """Check health of all backend services"""
            if not self.service_registry:
                return {
                    "status": "unhealthy",
                    "message": "Service registry not available",
                }

            try:
                services = self.service_registry.get_service_status()
                if not services:
                    return {
                        "status": "unhealthy",
                        "message": "No backend services registered",
                    }

                healthy_count = sum(
                    1 for s in services.values() if s.get("status") == "healthy"
                )
                total_count = len(services)

                unhealthy_services = [
                    name
                    for name, info in services.items()
                    if info.get("status") != "healthy"
                ]

                if healthy_count == total_count:
                    status = "healthy"
                    message = f"All {total_count} backend services are healthy"
                elif healthy_count > 0:
                    status = "degraded"
                    message = f"{healthy_count}/{total_count} backend services healthy"
                else:
                    status = "unhealthy"
                    message = "No backend services are healthy"

                return {
                    "status": status,
                    "message": message,
                    "details": {
                        "total_services": total_count,
                        "healthy_services": healthy_count,
                        "unhealthy_services": unhealthy_services,
                        "services": services,
                    },
                }
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "message": f"Failed to check backend services: {str(e)}",
                }

        self.add_check("basic", basic_check)
        self.add_check("backend_services", backend_services_check)


def create_api_gateway_health_check(
    service_name: str = "api_gateway",
    version: str = "1.0.0",
    service_registry: Optional[Any] = None,
) -> Dict[str, Any]:
    """Create basic API Gateway health check"""
    health_checker = APIGatewayHealthChecker(service_name)
    if service_registry:
        health_checker.set_service_registry(service_registry)
    health_checker.add_basic_checks()
    return health_checker.run_checks()
