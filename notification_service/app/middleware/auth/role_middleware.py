"""
Role-based authorization middleware for Notification Service.
Handles role-based access control at the middleware level.
"""

from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from notification_service.app.utils.logging import setup_notification_logging

logger = setup_notification_logging("notification_service_roles")


class NotificationServiceRoleAuthorizationMiddleware(BaseHTTPMiddleware):
    """
    Role-based authorization middleware for Notification Service.

    Features:
    - Path-based role requirements
    - Method-specific role checking
    - Flexible role configuration
    - Request authorization logging
    - Correlation ID integration
    """

    def __init__(
        self,
        app: Any,
        role_requirements: Optional[Dict[str, Union[str, List[str]]]] = None,
        exclude_paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.role_requirements = role_requirements or {}
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
        ]

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process role authorization for each request.
        """
        # Skip authorization for excluded paths
        if self._should_skip_auth(request.url.path):
            return await call_next(request)

        # Extract correlation ID
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        try:
            # Check if user is authenticated (should be done by auth middleware)
            user_id = getattr(request.state, "user_id", None)
            user_role = getattr(request.state, "user_role", None) or "user"
            user_roles: List[str] = getattr(request.state, "user_roles", None) or []

            if not user_id:
                # This should not happen if auth middleware is properly configured
                logger.warning(
                    "Role check attempted on unauthenticated request",
                    extra={
                        "correlation_id": correlation_id,
                        "path": request.url.path,
                        "method": request.method,
                        "service": "notification_service",
                        "event_type": "role_check_unauthenticated",
                    },
                )
                return await call_next(request)  # Let auth middleware handle this

            # Check role requirements for this path
            auth_result = self._check_role_authorization(
                request.url.path, request.method, user_role, user_roles
            )

            if auth_result["authorized"]:
                # Log successful authorization
                logger.info(
                    "Role authorization successful",
                    extra={
                        "correlation_id": correlation_id,
                        "user_id": user_id,
                        "user_role": user_role,
                        "required_roles": auth_result.get("required_roles", []),
                        "path": request.url.path,
                        "method": request.method,
                        "service": "notification_service",
                        "event_type": "role_auth_success",
                    },
                )

                # Process the request
                response = await call_next(request)
                return response

            else:
                # Authorization failed
                logger.warning(
                    f"Role authorization failed: {auth_result['reason']}",
                    extra={
                        "correlation_id": correlation_id,
                        "user_id": user_id,
                        "user_role": user_role,
                        "user_roles": user_roles,
                        "required_roles": auth_result.get("required_roles", []),
                        "path": request.url.path,
                        "method": request.method,
                        "reason": auth_result["reason"],
                        "service": "notification_service",
                        "event_type": "role_auth_failed",
                    },
                )

                # Return 403 Forbidden
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "type": "authorization_error",
                            "message": "Insufficient permissions",
                            "correlation_id": correlation_id,
                            "details": {
                                "reason": auth_result["reason"],
                                "required_roles": auth_result.get("required_roles", []),
                                "user_role": user_role,
                            },
                        }
                    },
                )

        except Exception as e:
            # Unexpected authorization error
            logger.error(
                f"Role authorization error: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(e),
                    "service": "notification_service",
                    "event_type": "role_auth_error",
                },
                exc_info=True,
            )

            # Return 500 for auth system errors
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "type": "authorization_system_error",
                        "message": "Authorization system error",
                        "correlation_id": correlation_id,
                    }
                },
            )

    def _should_skip_auth(self, path: str) -> bool:
        """
        Check if authorization should be skipped for this path.
        """
        # Check exact matches
        if path in self.exclude_paths:
            return True

        # Check prefix matches
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True

        return False

    def _check_role_authorization(
        self, path: str, method: str, user_role: str, user_roles: List[str]
    ) -> Dict[str, Any]:
        """
        Check if the user has required roles for the given path and method.

        Args:
            path: Request path
            method: HTTP method
            user_role: Primary user role
            user_roles: List of all user roles

        Returns:
            Dict with authorization result
        """
        # Check for exact path match
        required_roles = self.role_requirements.get(path)
        if required_roles:
            return self._validate_roles(required_roles, user_role, user_roles)

        # Check for path patterns (prefix matching)
        for req_path, roles in self.role_requirements.items():
            if path.startswith(req_path):
                return self._validate_roles(roles, user_role, user_roles)

        # No role requirements found for this path
        return {
            "authorized": True,
            "reason": "no_role_requirements",
        }

    def _validate_roles(
        self,
        required_roles: Union[str, List[str]],
        user_role: str,
        user_roles: List[str],
    ) -> Dict[str, Any]:
        """
        Validate if user has the required role(s).

        Args:
            required_roles: Required role(s) - can be string or list
            user_role: Primary user role
            user_roles: List of all user roles

        Returns:
            Dict with validation result
        """
        # Normalize required roles to list
        if isinstance(required_roles, str):
            required_roles = [required_roles]

        # Check if user has any of the required roles
        user_all_roles = set([user_role] + user_roles)

        for required_role in required_roles:
            if required_role in user_all_roles:
                return {
                    "authorized": True,
                    "required_roles": required_roles,
                    "matched_role": required_role,
                }

        return {
            "authorized": False,
            "reason": "insufficient_role",
            "required_roles": required_roles,
            "user_roles": list(user_all_roles),
        }


def setup_notification_role_authorization_middleware(
    app: FastAPI,
    role_requirements: Optional[Dict[str, Union[str, List[str]]]] = None,
    exclude_paths: Optional[List[str]] = None,
) -> None:
    """
    Setup role-based authorization middleware for Notification Service.

    Args:
        app: FastAPI application instance
        role_requirements: Dict mapping paths to required roles
        exclude_paths: List of paths to exclude from authorization

    Example role_requirements:
    {
        "/api/v1/bulk-notifications": "admin",  # Admin only for bulk operations
        "/notification-service": "admin",  # Management routes
    }
    """
    if exclude_paths is None:
        exclude_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
        ]

    if role_requirements is None:
        # Default role requirements for notification service patterns
        role_requirements = {
            "/api/v1/bulk-notifications": [
                "admin",
                "moderator",
            ],  # Bulk operations require admin/moderator
            "/notification-service": "admin",  # Management routes require admin
        }

    app.add_middleware(
        NotificationServiceRoleAuthorizationMiddleware,
        role_requirements=role_requirements,
        exclude_paths=exclude_paths,
    )

    logger.info(
        "Role authorization middleware configured",
        extra={
            "service": "notification_service",
            "role_requirements_count": len(role_requirements),
            "excluded_paths": exclude_paths,
            "event_type": "role_middleware_setup",
        },
    )
