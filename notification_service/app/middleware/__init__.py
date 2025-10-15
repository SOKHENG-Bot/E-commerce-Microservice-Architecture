"""
Notification Service middleware package.

This package provides various middleware components for the Notification Service:
- Authentication and authorization
- Request validation and security
- Error handling
- Logging
"""

from .auth import (
    AuthenticatedUser,
    NotificationServiceAuthMiddleware,
    NotificationServiceRoleAuthorizationMiddleware,
    setup_notification_auth_middleware,
    setup_notification_role_authorization_middleware,
)
from .error import setup_error_middleware
from .logging import create_enhanced_logger
from .validation import setup_validation_middleware

__all__ = [
    # Authentication & Authorization
    "AuthenticatedUser",
    "NotificationServiceAuthMiddleware",
    "NotificationServiceRoleAuthorizationMiddleware",
    "setup_notification_auth_middleware",
    "setup_notification_role_authorization_middleware",
    # Error handling
    "setup_error_middleware",
    # Logging
    "create_enhanced_logger",
    # Validation
    "setup_validation_middleware",
]
