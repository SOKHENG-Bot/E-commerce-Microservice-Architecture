"""
CORS middleware configuration for API Gateway
"""

from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.settings import GatewaySettings

# Import shared components
from app.utils.logging import setup_api_gateway_logging

logger = setup_api_gateway_logging("api_gateway_cors")


class CustomCORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware with enhanced logging"""

    def __init__(self, app: FastAPI, settings: GatewaySettings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process CORS with logging"""
        origin = request.headers.get("Origin")

        # Log cross-origin requests
        if (
            origin
            and origin not in self.settings.CORS_ORIGINS
            and "*" not in self.settings.CORS_ORIGINS
        ):
            logger.warning(
                "Blocked CORS request",
                extra={
                    "origin": origin,
                    "path": request.url.path,
                    "method": request.method,
                },
            )

        response = await call_next(request)
        return response


def setup_cors_middleware(app: FastAPI, settings: GatewaySettings) -> None:
    """Setup CORS middleware for API Gateway"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
        expose_headers=[
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
    )

    # Add custom CORS logging middleware
    # Note: This would need to be integrated differently in the main app
