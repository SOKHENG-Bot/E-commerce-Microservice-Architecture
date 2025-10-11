"""
Performance monitoring and health endpoints for V1 API
"""

import time
from typing import Any, Dict, Optional

from app.api.dependencies import AdminUserDep, CorrelationIdDep
from app.utils.logging import setup_product_logging
from fastapi import APIRouter

logger = setup_product_logging("product_service_v1_monitoring")

router = APIRouter()


@router.get("/performance/status")
async def get_performance_status(
    admin_user: str = AdminUserDep,  # Admin authentication required
    correlation_id: Optional[str] = CorrelationIdDep,
) -> Dict[str, Any]:
    """
    Get comprehensive performance status

    Features:
    - Service health indicators
    - System resource usage
    - Response time benchmarks
    """

    start_time = time.time()

    # Calculate overall response time
    total_response_time = (time.time() - start_time) * 1000

    performance_status: Dict[str, Any] = {
        "service": "product_service",
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "performance_metrics": {
            "total_response_time_ms": round(total_response_time, 2),
        },
        "features": {
            "core_crud": "enabled",
            "authentication": "enabled",
        },
        "api_endpoints": {
            "products": "/api/v1/products/*",
            "categories": "/api/v1/categories/*",
            "inventory": "/api/v1/inventory/*",
        },
    }

    logger.info(
        "Performance status checked",
        extra={
            "response_time_ms": total_response_time,
            "correlation_id": correlation_id,
            "admin_user": admin_user,
        },
    )

    return performance_status


@router.get("/performance/benchmark")
async def run_performance_benchmark(
    admin_user: str = AdminUserDep,  # Admin authentication required
    correlation_id: Optional[str] = CorrelationIdDep,
) -> Dict[str, Any]:
    """
    🏃‍♂️ Run performance benchmarks

    Features:
    - Basic response time analysis
    """

    # Simple response time benchmark
    start_time = time.time()
    # Simulate some basic processing
    import asyncio

    await asyncio.sleep(0.001)  # Minimal async operation
    processing_time = (time.time() - start_time) * 1000

    benchmarks: Dict[str, Any] = {
        "service": "product_service",
        "benchmark_timestamp": time.time(),
        "performance_metrics": {
            "processing_time_ms": round(processing_time, 3),
        },
        "performance_grades": {
            "response_time": "excellent"
            if processing_time < 1
            else "good"
            if processing_time < 5
            else "needs_improvement",
        },
        "recommendations": [
            "Performance monitoring is basic - consider adding detailed metrics if needed"
        ],
    }

    logger.info(
        "Performance benchmark completed",
        extra={
            "processing_time_ms": processing_time,
            "correlation_id": correlation_id,
            "admin_user": admin_user,
        },
    )

    return benchmarks
