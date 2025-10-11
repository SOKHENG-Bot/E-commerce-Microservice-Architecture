from typing import Any, Dict

from fastapi import APIRouter

from ...utils.health_check import (
    create_notification_service_health_check_async as create_basic_health_check,
)

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for the notification service using shared HealthChecker."""
    return await create_basic_health_check("notification-service", "1.0.0")
