"""
User Service Management API Routes
"""

from typing import Any, Dict, Union

from fastapi import APIRouter

from user_service.app.schemas.user import (
    ManagementErrorResponse,
    ManagementSuccessResponse,
)
from user_service.app.utils.logging import setup_user_logging

# Setup logger
logger = setup_user_logging("management")

router = APIRouter(prefix="/user-service", tags=["user-service-management"])


@router.get(
    "/metrics",
    summary="Get User Service metrics",
    response_model=Union[ManagementSuccessResponse, ManagementErrorResponse],
)
async def get_user_service_metrics() -> Union[
    ManagementSuccessResponse, ManagementErrorResponse
]:
    """Get comprehensive User Service metrics"""
    try:
        # Mock metrics data for now
        metrics_data: Dict[str, Any] = {
            "service": {
                "total_requests": 1000,
                "success_rate": 95.5,
                "error_rate": 4.5,
                "avg_response_time_ms": 150,
            },
            "recent_activity": {"recent_requests": 50, "recent_error_rate": 2.0},
        }

        # Note: Management endpoints typically don't need API event tracking
        # as they're operational/monitoring endpoints for internal use

        logger.info(
            f"User Service metrics requested: {metrics_data['service']['total_requests']} total requests"
        )

        return ManagementSuccessResponse(data=metrics_data)

    except Exception as e:
        logger.error(f"Error retrieving User Service metrics: {e}")
        return ManagementErrorResponse(
            message="Failed to retrieve metrics",
            error=str(e),
        )


@router.get(
    "/health/detailed",
    summary="Get detailed User Service health status",
    response_model=Union[ManagementSuccessResponse, ManagementErrorResponse],
)
async def get_detailed_user_service_health() -> Union[
    ManagementSuccessResponse, ManagementErrorResponse
]:
    """Get detailed health status including metrics-based health"""
    try:
        # Mock health data
        health_status = "healthy"

        health_data: Dict[str, Any] = {
            "service": "user_service",
            "overall_status": health_status,
            "metrics_health": {"status": "healthy"},
            "health_checks": {"status": "healthy"},
        }

        logger.info(f"User Service detailed health check: {health_status}")

        return ManagementSuccessResponse(data=health_data)

    except Exception as e:
        logger.error(f"Error retrieving User Service detailed health: {e}")
        return ManagementErrorResponse(
            message="Failed to retrieve detailed health status",
            error=str(e),
        )


@router.get(
    "/status",
    summary="Get User Service operational status",
    response_model=Union[ManagementSuccessResponse, ManagementErrorResponse],
)
async def get_user_service_status() -> Union[
    ManagementSuccessResponse, ManagementErrorResponse
]:
    """Get current operational status of User Service"""
    try:
        # Mock status data
        operational_status = "operational"

        status_data: Dict[str, Any] = {
            "service": "user_service",
            "operational_status": operational_status,
            "total_requests": 1000,
            "success_rate": 95.5,
            "error_rate": 4.5,
            "avg_response_time_ms": 150,
            "recent_activity": {"recent_requests": 50, "recent_error_rate": 2.0},
        }

        logger.info(f"User Service status requested: {operational_status}")

        return ManagementSuccessResponse(data=status_data)

    except Exception as e:
        logger.error(f"Error retrieving User Service status: {e}")
        return ManagementErrorResponse(
            message="Failed to retrieve service status",
            error=str(e),
        )


@router.get(
    "/config",
    summary="Get User Service configuration",
    response_model=Union[ManagementSuccessResponse, ManagementErrorResponse],
)
async def get_user_service_config() -> Union[
    ManagementSuccessResponse, ManagementErrorResponse
]:
    """Get current User Service configuration (non-sensitive values)"""
    try:
        # Mock configuration data
        config_info: Dict[str, Any] = {
            "service_name": "User Service",
            "version": "1.0.0",
            "environment": "development",
            "debug_mode": True,
            "cors_enabled": True,
            "metrics_enabled": True,
            "validation_enabled": True,
            "logging_level": "INFO",
            "middleware_count": 6,
            "endpoints_count": 25,
            "management_endpoints": 5,
        }

        logger.info("User Service configuration requested")

        return ManagementSuccessResponse(data=config_info)

    except Exception as e:
        logger.error(f"Error retrieving User Service configuration: {e}")
        return ManagementErrorResponse(
            message="Failed to retrieve configuration",
            error=str(e),
        )
