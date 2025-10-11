"""
Security middleware for Order Service.
"""

from .validation_middleware import (
    OrderServiceRequestValidationMiddleware,
    setup_order_request_validation_middleware,
)

__all__ = [
    "OrderServiceRequestValidationMiddleware",
    "setup_order_request_validation_middleware",
]
