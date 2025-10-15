"""
Authentication middleware for Notification Service.
Handles JWT token validation, user context extraction, and authorization.
"""

from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Import dependencies for JWT handling
from notification_service.app.core.settings import get_settings
from notification_service.app.utils.jwt_handler import NotificationJWTHandler
from notification_service.app.utils.logging import setup_notification_logging

logger = setup_notification_logging("notification_service_auth")


class NotificationServiceAuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for Notification Service.

    Features:
    - JWT token validation
    - User context extraction
    - Role-based access control
    - Request authentication logging
    - Correlation ID integration
    """

    def __init__(
        self,
        app: Any,
        exclude_paths: Optional[list[str]] = None,
        jwt_handler: Optional[Any] = None,
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
        ]

        # Use provided JWT handler or create default one
        if jwt_handler:
            self.jwt_handler = jwt_handler
        else:
            settings = get_settings()
            self.jwt_handler = NotificationJWTHandler(
                secret_key=settings.SECRET_KEY, algorithm=settings.ALGORITHM
            )

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process authentication for each request.
        """
        # Skip authentication for excluded paths
        if self._should_skip_auth(request.url.path):
            return await call_next(request)

        # Extract correlation ID
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        try:
            # Extract and validate token
            auth_result = await self._authenticate_request(request)

            if auth_result["authenticated"]:
                # Add user context to request state
                request.state.user_id = auth_result["user_id"]
                request.state.user_role = auth_result["user_role"]
                request.state.token_data = auth_result["token_data"]

                # Log successful authentication
                logger.info(
                    "Request authenticated",
                    extra={
                        "correlation_id": correlation_id,
                        "user_id": auth_result["user_id"],
                        "user_role": auth_result["user_role"],
                        "token_source": auth_result.get("token_source", "unknown"),
                        "path": request.url.path,
                        "method": request.method,
                        "service": "notification_service",
                        "event_type": "auth_success",
                    },
                )

                # Process the request
                response = await call_next(request)
                return response

            else:
                # Authentication failed
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
                        "service": "notification_service",
                        "event_type": "auth_failed",
                    },
                )

                # Return 401 Unauthorized
                from fastapi.responses import JSONResponse

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
            # Unexpected authentication error
            logger.error(
                f"Authentication error: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(e),
                    "service": "notification_service",
                    "event_type": "auth_error",
                },
                exc_info=True,
            )

            # Return 500 for auth system errors
            from fastapi.responses import JSONResponse

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

    def _should_skip_auth(self, path: str) -> bool:
        """
        Check if authentication should be skipped for this path.
        """
        # Check exact matches
        if path in self.exclude_paths:
            return True

        # Check prefix matches (for API versioning)
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True

        return False

    async def _authenticate_request(self, request: Request) -> Dict[str, Any]:
        """
        Authenticate the request using cookie tokens only.

        Checks for authentication tokens in cookies.
        No Authorization header support.

        Returns:
            Dict with authentication result
        """
        try:
            # Only check cookies for authentication tokens
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

            # Validate token
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
        """
        Validate JWT token and extract claims using JWTHandler.

        Performs proper JWT validation with signature verification and expiration checking.
        """
        try:
            # Decode and validate token using injected JWT handler
            token_data = self.jwt_handler.decode_token(token)

            # Convert TokenData to dict format expected by middleware
            return {
                "user_id": token_data.user_id,
                "email": token_data.email,
                "username": token_data.username,
                "role": token_data.roles[0]
                if token_data.roles
                else "user",  # Primary role
                "roles": token_data.roles,
                "permissions": token_data.permissions,
                "exp": int(token_data.expires_at.timestamp()),
                "iat": token_data.expires_at.timestamp()
                - 3600,  # Approximate issued time
                "token_type": "access",
            }

        except ValueError as e:
            # Token validation failed (expired, invalid signature, etc.)
            logger.warning(f"JWT validation failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"JWT processing error: {str(e)}")
            return None


class AuthenticatedUser:
    """
    Dependency class for FastAPI route authentication.
    Use this in your route handlers to ensure authentication.
    """

    def __init__(self, required_role: Optional[str] = None):
        self.required_role = required_role

    async def __call__(self, request: Request) -> Dict[str, Any]:
        """
        FastAPI dependency that ensures user is authenticated.
        """
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


def setup_notification_auth_middleware(
    app: FastAPI,
    exclude_paths: Optional[list[str]] = None,
    jwt_handler: Optional[Any] = None,
) -> None:
    """
    Setup authentication middleware for Notification Service.

    Args:
        app: FastAPI application instance
        exclude_paths: List of paths to exclude from authentication
        jwt_handler: Optional JWT handler instance to use for token validation
    """
    if exclude_paths is None:
        exclude_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
        ]

    app.add_middleware(
        NotificationServiceAuthMiddleware,
        exclude_paths=exclude_paths,
        jwt_handler=jwt_handler,
    )

    logger.info(
        "Notification Service authentication middleware configured",
        extra={
            "service": "notification_service",
            "excluded_paths": exclude_paths,
            "jwt_handler_provided": jwt_handler is not None,
            "event_type": "auth_middleware_setup",
        },
    )


# Convenience instances for route dependencies
authenticated_user = AuthenticatedUser()  # Any authenticated user
admin_user = AuthenticatedUser(required_role="admin")  # Admin only
moderator_user = AuthenticatedUser(required_role="moderator")  # Moderator or admin
