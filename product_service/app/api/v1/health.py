from typing import Any, Dict

from fastapi import APIRouter

from ...utils.service_health import (
    create_product_service_health_check as create_basic_health_check,
)

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for the product service using shared HealthChecker."""
    return create_basic_health_check("product-service", "1.0.0")
