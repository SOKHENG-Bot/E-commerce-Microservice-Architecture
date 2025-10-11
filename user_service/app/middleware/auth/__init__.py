"""
Authentication middleware package for User Service.
"""

from .auth_middleware import (
    AuthenticatedUser,
    UserServiceAuthMiddleware,
    admin_user,
    authenticated_user,
    moderator_user,
    setup_user_auth_middleware,
)

__all__ = [
    "UserServiceAuthMiddleware",
    "AuthenticatedUser",
    "setup_user_auth_middleware",
    "authenticated_user",
    "admin_user",
    "moderator_user",
]
