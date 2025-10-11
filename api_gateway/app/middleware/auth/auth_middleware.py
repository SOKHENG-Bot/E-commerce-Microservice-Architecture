"""
Authentication middleware for API Gateway using shared JWT
"""

from typing import Awaitable, Callable

from fastapi import HTTPException, Request, Response, status
from fastapi.security.utils import get_authorization_scheme_param

from app.config.settings import GatewaySettings

# Import shared components
# Import local components
from app.utils.jwt_handler import JWTHandler, TokenData
from app.utils.logging import setup_api_gateway_logging

logger = setup_api_gateway_logging("api_gateway_auth")


class AuthMiddleware:
    """JWT Authentication middleware using shared components"""

    def __init__(self, settings: GatewaySettings):
        self.settings = settings
        # Use shared JWT handler
        self.jwt_handler = JWTHandler(settings.SECRET_KEY, settings.JWT_ALGORITHM)

        # Public endpoints that don't require authentication
        self.public_endpoints = {
            "/health",
            "/health/detailed",
            "/health/ready",
            "/health/live",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/products",  # Public product browsing
            "/api/v1/categories",  # Public category browsing
        }

        # Endpoints that require authentication
        self.protected_patterns = [
            "/api/v1/users/",
            "/api/v1/profiles/",
            "/api/v1/addresses/",
            "/api/v1/orders/",
            "/api/v1/auth/logout",
        ]

    async def __call__(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process authentication middleware"""
        path = request.url.path

        # Skip authentication for public endpoints
        if self._is_public_endpoint(path):
            return await call_next(request)

        # Check if endpoint requires authentication
        if not self._requires_authentication(path):
            return await call_next(request)

        # Extract and validate JWT token
        try:
            token_data = await self._extract_and_validate_token(request)
            request.state.current_user = token_data
            request.state.user_id = str(token_data.user_id)

            logger.info(
                "Authenticated request",
                extra={
                    "user_id": str(token_data.user_id),
                    "email": token_data.email,
                    "path": path,
                    "method": request.method,
                },
            )

        except HTTPException as e:
            logger.warning(
                "Authentication failed",
                extra={"path": path, "method": request.method, "error": e.detail},
            )
            raise

        return await call_next(request)

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public"""
        return path in self.public_endpoints or path.startswith("/static/")

    def _requires_authentication(self, path: str) -> bool:
        """Check if endpoint requires authentication"""
        return any(path.startswith(pattern) for pattern in self.protected_patterns)

    async def _extract_and_validate_token(self, request: Request) -> TokenData:
        """Extract and validate JWT token from request"""
        # Get Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Parse Bearer token
        scheme, token = get_authorization_scheme_param(authorization)
        if not token or scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate token using shared JWT handler
        try:
            token_data = self.jwt_handler.decode_token(token)
            return token_data
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
