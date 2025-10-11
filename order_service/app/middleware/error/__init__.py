"""
Error middleware for Order Service.
"""

from .error_handler import OrderServiceErrorHandler, setup_order_error_handling

__all__ = ["OrderServiceErrorHandler", "setup_order_error_handling"]
