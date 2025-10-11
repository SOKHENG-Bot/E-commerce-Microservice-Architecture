"""
Request size validation middleware
"""

import json
from typing import TYPE_CHECKING, Any, Callable, Dict

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from fastapi import FastAPI
    from starlette.responses import Response

from app.utils.logging import setup_api_gateway_logging

logger = setup_api_gateway_logging("api_gateway_validation")


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate request size and basic format"""

    def __init__(
        self, app: "FastAPI", max_request_size: int = 10 * 1024 * 1024
    ):  # 10MB
        super().__init__(app)
        self.max_request_size = max_request_size

        # Request size limits per endpoint
        self.size_limits = {
            "/api/v1/users/avatar": 5 * 1024 * 1024,  # 5MB for avatar uploads
            "/api/v1/products/images": 10 * 1024 * 1024,  # 10MB for product images
        }

    def _get_content_length(self, request: Request) -> int:
        """Get request content length"""
        content_length = request.headers.get("content-length")
        if content_length:
            return int(content_length)
        return 0

    def _validate_request_size(self, request: Request):
        """Validate request size limits"""
        content_length = self._get_content_length(request)

        # Check specific endpoint limits
        for endpoint, limit in self.size_limits.items():
            if request.url.path.startswith(endpoint):
                if content_length > limit:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Request size {content_length} exceeds limit {limit} for {endpoint}",
                    )
                return

        # Check global limit
        if content_length > self.max_request_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Request size {content_length} exceeds maximum {self.max_request_size}",
            )

    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> "Response":
        # Validate request size for uploads
        if request.method in ["POST", "PUT", "PATCH"]:
            self._validate_request_size(request)

            # Basic JSON validation for API endpoints
            if request.url.path.startswith(
                "/api/"
            ) and "application/json" in request.headers.get("content-type", ""):
                try:
                    body = await request.body()
                    if body:
                        json.loads(body)  # Just validate it's valid JSON

                        # Create new receive function to restore the body
                        async def receive() -> Dict[str, Any]:
                            return {
                                "type": "http.request",
                                "body": body,
                                "more_body": False,
                            }

                        request._receive = receive  # type: ignore[attr-defined]

                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid JSON in request body",
                    )

        return await call_next(request)
