"""
Authentication middleware for Order Service.
"""

from .auth_middleware import (
    AuthenticatedUser,
    OrderServiceAuthMiddleware,
    admin_user,
    authenticated_user,
    setup_order_auth_middleware,
)
from .role_middleware import (
    OrderServiceRoleAuthorizationMiddleware,
    setup_order_role_authorization_middleware,
)

__all__ = [
    "OrderServiceAuthMiddleware",
    "AuthenticatedUser",
    "setup_order_auth_middleware",
    "authenticated_user",
    "admin_user",
    "OrderServiceRoleAuthorizationMiddleware",
    "setup_order_role_authorization_middleware",
]
