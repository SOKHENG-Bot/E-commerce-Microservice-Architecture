from typing import Any, Awaitable, Callable, Dict, List, Optional, Union, cast

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from user_service.app.utils.logging import setup_user_logging

logger = setup_user_logging("user_service_roles")


class UserServiceRoleAuthorizationMiddleware(BaseHTTPMiddleware):
    """Middleware to authorize requests based on user roles."""

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
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
        ]

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Middleware to authorize requests based on user roles."""

        if self._should_skip_auth(request.url.path):
            return await call_next(request)

        correlation_id = getattr(request.state, "correlation_id", "unknown")

        try:
            user_id = getattr(request.state, "user_id", None)
            user_role = getattr(request.state, "user_role", None) or "user"
            user_roles = (
                cast(List[str], getattr(request.state, "user_roles", None)) or []
            )

            if not user_id:
                logger.warning(
                    "Role check attempted on unauthenticated request",
                    extra={
                        "correlation_id": correlation_id,
                        "path": request.url.path,
                        "method": request.method,
                        "service": "user_service",
                        "event_type": "role_check_unauthenticated",
                    },
                )
                return await call_next(request)

            auth_result = self._check_role_authorization(
                request.url.path, request.method, user_role, user_roles
            )

            if auth_result["authorized"]:
                logger.info(
                    "Role authorization successful",
                    extra={
                        "correlation_id": correlation_id,
                        "user_id": user_id,
                        "user_role": user_role,
                        "required_roles": auth_result.get("required_roles", []),
                        "path": request.url.path,
                        "method": request.method,
                        "service": "user_service",
                        "event_type": "role_auth_success",
                    },
                )

                response = await call_next(request)
                return response

            else:
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
                        "service": "user_service",
                        "event_type": "role_auth_failed",
                    },
                )

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
            logger.error(
                f"Role authorization error: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(e),
                    "service": "user_service",
                    "event_type": "role_auth_error",
                },
                exc_info=True,
            )

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
        """Check if the request path should skip role authorization."""

        if path in self.exclude_paths:
            return True

        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False

    def _check_role_authorization(
        self, path: str, method: str, user_role: str, user_roles: List[str]
    ) -> Dict[str, Any]:
        """Check if the user has the required role for the given path and method."""

        required_roles = self.role_requirements.get(path)
        if required_roles:
            return self._validate_roles(required_roles, user_role, user_roles)

        for req_path, roles in self.role_requirements.items():
            if path.startswith(req_path):
                return self._validate_roles(roles, user_role, user_roles)

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
        """Validate if the user has one of the required roles."""

        if isinstance(required_roles, str):
            required_roles = [required_roles]

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


def setup_user_role_authorization_middleware(
    app: FastAPI,
    role_requirements: Optional[Dict[str, Union[str, List[str]]]] = None,
    exclude_paths: Optional[List[str]] = None,
) -> None:
    """Setup role authorization middleware for the User Service."""

    if exclude_paths is None:
        exclude_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
        ]

    if role_requirements is None:
        role_requirements = {
            "/api/v1/users": [
                "admin",
                "moderator",
            ],
            "/api/v1/permissions": "admin",
            "/user-service": "admin",
            "/api/v1/bulk": [
                "admin",
                "moderator",
            ],
        }

    app.add_middleware(
        UserServiceRoleAuthorizationMiddleware,
        role_requirements=role_requirements,
        exclude_paths=exclude_paths,
    )

    logger.info(
        "Role authorization middleware configured",
        extra={
            "service": "user_service",
            "role_requirements_count": len(role_requirements),
            "excluded_paths": exclude_paths,
            "event_type": "role_middleware_setup",
        },
    )
