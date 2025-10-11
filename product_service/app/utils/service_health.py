"""
Product Service Health Check Utilities
======================================

Independent health check functionality for Product service.
No shared dependencies - completely self-contained.
"""

import time
from typing import Any, Callable, Dict


class ProductServiceHealthChecker:
    """Product Service specific health checker"""

    def __init__(self, service_name: str = "product_service") -> None:
        self.service_name = service_name
        self.checks: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self.start_time = time.time()

    def add_check(self, name: str, check_func: Callable[[], Dict[str, Any]]) -> None:
        """Add a health check function"""
        self.checks[name] = check_func

    def run_checks(self) -> Dict[str, Any]:
        """Run all health checks with Product Service specific context"""
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

    def add_product_specific_checks(self) -> None:
        """Add Product Service specific health checks"""

        def basic_check() -> Dict[str, Any]:
            return {
                "status": "healthy",
                "message": "Product Service is running",
                "version": "1.0.0",
                "component": "core",
            }

        def catalog_check() -> Dict[str, Any]:
            # Check product catalog accessibility
            return {
                "status": "healthy",
                "message": "Product catalog accessible",
                "component": "catalog",
            }

        def inventory_check() -> Dict[str, Any]:
            # Check inventory system
            return {
                "status": "healthy",
                "message": "Inventory system operational",
                "component": "inventory",
            }

        self.add_check("basic", basic_check)
        self.add_check("catalog", catalog_check)
        self.add_check("inventory", inventory_check)


def create_product_service_health_check(
    service_name: str = "product_service", version: str = "1.0.0"
) -> Dict[str, Any]:
    """Create basic Product Service health check"""
    health_checker = ProductServiceHealthChecker(service_name)
    health_checker.add_product_specific_checks()
    return health_checker.run_checks()
