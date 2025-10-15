"""
Health API endpoints
"""

import time

from fastapi import APIRouter

from user_service.app.schemas.user import HealthResponse
from user_service.app.utils.logging import setup_user_logging
from user_service.app.utils.service_health import create_user_service_health_check

# Setup logger
logger = setup_user_logging("health")

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for the user service using shared HealthChecker."""
    try:
        result = create_user_service_health_check("user-service", "1.0.0")

        # Note: Health checks typically don't need API event tracking
        # as they're monitoring endpoints, but can be enabled for analytics

        logger.info(f"Health check completed: {result.get('status', 'unknown')}")
        return HealthResponse(
            status=result.get("status", "unknown"),
            service=result.get("service", "user-service"),
            version="1.0.0",
            timestamp=str(result.get("timestamp", "")),
            uptime_seconds=result.get("uptime_seconds", 0.0),
            database=result.get("checks", {}).get("database", {}),
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            service="user-service",
            version="1.0.0",
            timestamp=str(time.time()),
            uptime_seconds=0.0,
            database={"error": str(e)},
        )
