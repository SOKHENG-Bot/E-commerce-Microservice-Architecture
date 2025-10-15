"""
Authentication and authorization middleware for Notification Service.
"""

from .auth_middleware import (
    AuthenticatedUser,
    NotificationServiceAuthMiddleware,
    setup_notification_auth_middleware,
)
from .role_middleware import (
    NotificationServiceRoleAuthorizationMiddleware,
    setup_notification_role_authorization_middleware,
)

__all__ = [
    # Authentication
    "AuthenticatedUser",
    "NotificationServiceAuthMiddleware",
    "setup_notification_auth_middleware",
    # Authorization
    "NotificationServiceRoleAuthorizationMiddleware",
    "setup_notification_role_authorization_middleware",
]
