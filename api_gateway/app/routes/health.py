"""
Health check endpoints for API Gateway using shared HealthChecker
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status

from ..utils.health_check import APIGatewayHealthChecker as HealthChecker
from ..utils.logging import setup_api_gateway_logging

logger = setup_api_gateway_logging("api_gateway_health")

router = APIRouter(tags=["health"])

# Create health checker instance
health_checker = HealthChecker("api-gateway")


async def get_service_registry():
    """Get service registry from app context"""
    from app.main import components

    return components.get("service_registry")


async def get_rate_limiter():
    """Get rate limiter from app context"""
    from app.main import components

    return components.get("rate_limiter")


@router.get("/health")
async def basic_health_check() -> Dict[str, Any]:
    """Basic health check for API Gateway with backend services"""

    service_registry = await get_service_registry()

    # Create fresh health checker for this request
    checker = HealthChecker("api-gateway")
    checker.set_service_registry(service_registry)
    checker.add_basic_checks()

    return checker.run_checks()


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check including all components"""

    service_registry = await get_service_registry()
    rate_limiter = await get_rate_limiter()

    # Create detailed health checker
    detailed_checker = HealthChecker("api-gateway-detailed")
    detailed_checker.set_service_registry(service_registry)
    detailed_checker.add_basic_checks()

    # Add additional gateway-specific checks
    def gateway_components_check() -> Dict[str, Any]:
        return {
            "status": "healthy",
            "message": "Gateway components operational",
            "details": {
                "rate_limiter": "connected"
                if rate_limiter and rate_limiter.redis_client
                else "disconnected",
                "middleware": "active",
                "routing": "active",
            },
        }

    def redis_connectivity_check() -> Dict[str, Any]:
        if rate_limiter and rate_limiter.redis_client:
            return {
                "status": "healthy",
                "message": "Redis connection active",
                "details": {"connection": "active", "component": "rate_limiter"},
            }
        else:
            return {
                "status": "unhealthy",
                "message": "Redis connection not available",
                "details": {"connection": "inactive", "component": "rate_limiter"},
            }

    detailed_checker.add_check("gateway_components", gateway_components_check)
    detailed_checker.add_check("redis_connectivity", redis_connectivity_check)

    return detailed_checker.run_checks()


@router.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """Kubernetes readiness probe - checks critical services"""

    service_registry = await get_service_registry()

    # Create readiness health checker
    readiness_checker = HealthChecker("api-gateway-readiness")
    readiness_checker.set_service_registry(service_registry)

    def critical_services_check() -> Dict[str, Any]:
        if not service_registry:
            return {
                "status": "unhealthy",
                "message": "Service registry not available",
                "details": {"critical_services": [], "healthy_critical": []},
            }

        services_health = service_registry.get_service_status()
        critical_services = ["user-service", "product-service", "order-service"]
        healthy_critical = [
            name
            for name in critical_services
            if services_health.get(name, {}).get("status") == "healthy"
        ]

        if not healthy_critical:
            return {
                "status": "unhealthy",
                "message": "No critical backend services are healthy",
                "details": {
                    "critical_services": critical_services,
                    "healthy_critical": healthy_critical,
                },
            }

        return {
            "status": "healthy",
            "message": f"{len(healthy_critical)}/{len(critical_services)} "
            "critical services ready",
            "details": {
                "critical_services": critical_services,
                "healthy_critical": healthy_critical,
            },
        }

    readiness_checker.add_check("critical_services", critical_services_check)
    result = readiness_checker.run_checks()

    # Check if any checks failed for HTTP 503 response
    unhealthy_checks = [
        check_result
        for check_result in result["checks"].values()
        if check_result.get("status") == "unhealthy"
    ]

    if unhealthy_checks:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result,
        )

    return result


@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}
