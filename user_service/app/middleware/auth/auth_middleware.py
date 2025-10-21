from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

from user_service.app.core.settings import get_settings
from user_service.app.utils.jwt_handler import JWTHandler
from user_service.app.utils.logging import setup_user_logging

logger = setup_user_logging("user_service_auth")
settings = get_settings()


class UserServiceAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to authenticate requests using JWT tokens from cookies."""

    def __init__(self, app: Any, exclude_paths: Optional[list[str]] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
        ]
        self.security = HTTPBearer(auto_error=False)
        self.jwt_handler = JWTHandler(
            secret_key=settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )

    def _should_skip_auth(self, path: str) -> bool:
        """Check if the request path should skip authentication."""

        if path in self.exclude_paths:
            return True

        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Middleware to authenticate requests using JWT tokens from cookies."""

        if self._should_skip_auth(request.url.path):
            return await call_next(request)

        correlation_id = getattr(request.state, "correlation_id", "unknown")

        try:
            auth_result = await self._authenticate_request(request)

            if auth_result["authenticated"]:
                request.state.user_id = auth_result["user_id"]
                request.state.user_role = auth_result["user_role"]
                request.state.token_data = auth_result["token_data"]

                logger.info(
                    "Request authenticated",
                    extra={
                        "correlation_id": correlation_id,
                        "user_id": auth_result["user_id"],
                        "user_role": auth_result["user_role"],
                        "token_source": auth_result.get("token_source", "unknown"),
                        "path": request.url.path,
                        "method": request.method,
                        "service": "user_service",
                        "event_type": "auth_success",
                    },
                )
                response = await call_next(request)
                return response

            else:
                logger.warning(
                    f"Authentication failed: {auth_result['reason']}",
                    extra={
                        "correlation_id": correlation_id,
                        "path": request.url.path,
                        "method": request.method,
                        "reason": auth_result["reason"],
                        "has_auth_cookie": bool(
                            request.cookies.get("auth_token")
                            or request.cookies.get("access_token")
                        ),
                        "service": "user_service",
                        "event_type": "auth_failed",
                    },
                )

                return JSONResponse(
                    status_code=401,
                    content={
                        "error": {
                            "type": "authentication_error",
                            "message": "Authentication required",
                            "correlation_id": correlation_id,
                            "details": {"reason": auth_result["reason"]},
                        }
                    },
                )

        except Exception as e:
            logger.error(
                f"Authentication error: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(e),
                    "service": "user_service",
                    "event_type": "auth_error",
                },
                exc_info=True,
            )

            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "type": "authentication_system_error",
                        "message": "Authentication system error",
                        "correlation_id": correlation_id,
                    }
                },
            )

    async def _authenticate_request(self, request: Request) -> Dict[str, Any]:
        """Authenticate the request using JWT token from cookies."""

        try:
            token = request.cookies.get("auth_token") or request.cookies.get(
                "access_token"
            )
            if not token:
                return {
                    "authenticated": False,
                    "reason": "missing_auth_cookie",
                }
            if (
                not token
                or token == "null"
                or token == "undefined"
                or token.strip() == ""
            ):
                return {"authenticated": False, "reason": "empty_cookie_token"}

            token_data = await self._validate_token(token)

            if not token_data:
                return {"authenticated": False, "reason": "invalid_cookie_token"}

            return {
                "authenticated": True,
                "user_id": token_data.get("user_id", "unknown"),
                "user_role": token_data.get("role", "user"),
                "token_data": token_data,
                "token_source": "cookie",
            }

        except Exception as e:
            logger.error(f"Cookie token validation error: {str(e)}")
            return {"authenticated": False, "reason": "cookie_validation_error"}

    async def _validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return token data."""

        try:
            token_data = self.jwt_handler.decode_token(token)
            return {
                "user_id": token_data.user_id,
                "email": token_data.email,
                "username": token_data.username,
                "role": token_data.roles[0] if token_data.roles else "user",
                "roles": token_data.roles,
                "permissions": token_data.permissions,
                "exp": int(token_data.expires_at.timestamp()),
                "iat": token_data.expires_at.timestamp() - 3600,
                "token_type": "access",
            }

        except ValueError as e:
            logger.warning(f"JWT validation failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"JWT processing error: {str(e)}")
            return None


class AuthenticatedUser:
    """Dependency to get authenticated user info from request."""

    def __init__(self, required_role: Optional[str] = None):
        self.required_role = required_role

    async def __call__(self, request: Request) -> Dict[str, Any]:
        user_id = getattr(request.state, "user_id", None)
        user_role = getattr(request.state, "user_role", None)

        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        if self.required_role and user_role != self.required_role:
            raise HTTPException(
                status_code=403, detail=f"Required role: {self.required_role}"
            )

        return {
            "user_id": user_id,
            "role": user_role,
            "token_data": getattr(request.state, "token_data", {}),
        }


def setup_user_auth_middleware(
    app: FastAPI,
    exclude_paths: Optional[list[str]] = None,
) -> None:
    """Setup authentication middleware for the User Service."""

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

    app.add_middleware(UserServiceAuthMiddleware, exclude_paths=exclude_paths)

    logger.info(
        "User Service authentication middleware configured",
        extra={
            "service": "user_service",
            "excluded_paths": exclude_paths,
            "event_type": "auth_middleware_setup",
        },
    )


authenticated_user = AuthenticatedUser()
admin_user = AuthenticatedUser(required_role="admin")
moderator_user = AuthenticatedUser(required_role="moderator")
