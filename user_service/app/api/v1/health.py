from typing import Any, Dict

from fastapi import APIRouter

from user_service.app.utils.logging import setup_user_logging
from user_service.app.utils.service_health import create_user_service_health_check

# Setup logger
logger = setup_user_logging("health")

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for the user service using shared HealthChecker."""
    try:
        result = create_user_service_health_check("user-service", "1.0.0")

        # Note: Health checks typically don't need API event tracking
        # as they're monitoring endpoints, but can be enabled for analytics

        logger.info(f"Health check completed: {result.get('status', 'unknown')}")
        return result

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}
