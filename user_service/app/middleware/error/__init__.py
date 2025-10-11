"""
Error handling middleware package for User Service.
"""

from .error_handler import UserServiceErrorHandler, setup_user_error_handling

__all__ = ["UserServiceErrorHandler", "setup_user_error_handling"]
