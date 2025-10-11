"""
Validation middleware for request/response validation, security, and input sanitization.
"""

import json
import re
from typing import Any, Dict, List, Optional, Set

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint

from ...utils.logging import setup_notification_logging

logger = setup_notification_logging("validation_middleware")


class ValidationMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive validation middleware for security and input sanitization.

    Features:
    - Request size limits
    - Content type validation
    - Input sanitization (XSS prevention)
    - SQL injection basic checks
    - Request logging
    - Rate limiting preparation
    """

    def __init__(
        self,
        app: Any,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB default
        allowed_content_types: Optional[List[str]] = None,
        enable_xss_protection: bool = True,
        enable_sql_injection_check: bool = True,
        enable_logging: bool = True,
    ):
        super().__init__(app)
        self.max_request_size = max_request_size
        self.allowed_content_types = allowed_content_types or [
            "application/json",
            "multipart/form-data",
            "application/x-www-form-urlencoded",
            "text/plain",
        ]
        self.enable_xss_protection = enable_xss_protection
        self.enable_sql_injection_check = enable_sql_injection_check
        self.enable_logging = enable_logging

        # XSS patterns
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"vbscript:",
            r"onload=",
            r"onerror=",
            r"onclick=",
            r"<iframe[^>]*>.*?</iframe>",
            r"<object[^>]*>.*?</object>",
            r"<embed[^>]*>.*?</embed>",
        ]

        # SQL injection patterns (basic)
        self.sql_injection_patterns = [
            r"(\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(select|from|where|into)\b)",
            r"(\bor\b\s+\d+\s*=\s*\d+)",
            r"(\band\b\s+\d+\s*=\s*\d+)",
            r"(--|#|/\*|\*/)",
            r"(\bexec\b|\bexecute\b|\bxp_cmdshell\b)",
        ]

        logger.info(
            "Validation middleware initialized",
            extra={
                "max_request_size_mb": max_request_size / (1024 * 1024),
                "allowed_content_types": allowed_content_types,
                "xss_protection_enabled": enable_xss_protection,
                "sql_injection_check_enabled": enable_sql_injection_check,
                "logging_enabled": enable_logging,
            },
        )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process each request through validation middleware."""

        # Request validation
        await self._validate_request(request)

        # Get response
        response = await call_next(request)

        # Response validation (optional)
        await self._validate_response(request, response)

        return response

    async def _validate_request(self, request: Request) -> None:
        """Validate incoming request."""

        try:
            # Check request size
            await self._validate_request_size(request)

            # Check content type
            await self._validate_content_type(request)

            # Read and validate request body if present
            if await self._has_request_body(request):
                body = await self._read_request_body(request)
                await self._validate_request_body(request, body)

            # Log request if enabled
            if self.enable_logging:
                self._log_request(request)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Request validation error",
                extra={
                    "error": str(e),
                    "path": request.url.path,
                    "method": request.method,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request validation failed",
            )

    async def _validate_request_size(self, request: Request) -> None:
        """Validate request size doesn't exceed limits."""
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_request_size:
                    logger.warning(
                        "Request size exceeds limit",
                        extra={
                            "content_length": size,
                            "max_allowed": self.max_request_size,
                            "path": request.url.path,
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Request size {size} bytes exceeds maximum allowed size {self.max_request_size} bytes",
                    )
            except ValueError:
                pass  # Invalid content-length header, skip validation

    async def _validate_content_type(self, request: Request) -> None:
        """Validate content type is allowed."""
        content_type = request.headers.get("content-type", "").split(";")[0].strip()

        # Skip validation for GET/HEAD requests or if no content type
        if request.method in ["GET", "HEAD"] or not content_type:
            return

        # Check if content type is allowed
        if content_type not in self.allowed_content_types:
            logger.warning(
                "Invalid content type",
                extra={
                    "content_type": content_type,
                    "allowed_types": self.allowed_content_types,
                    "path": request.url.path,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Content type '{content_type}' is not supported. Allowed types: {', '.join(self.allowed_content_types)}",
            )

    async def _has_request_body(self, request: Request) -> bool:
        """Check if request has a body."""
        return request.method in ["POST", "PUT", "PATCH"] and request.headers.get("content-length", "0") != "0"

    async def _read_request_body(self, request: Request) -> bytes:
        """Read request body for validation."""
        body = await request.body()

        # Reset body for next middleware/endpoint
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive
        return body

    async def _validate_request_body(self, request: Request, body: bytes) -> None:
        """Validate request body content."""
        try:
            # Try to parse as JSON for JSON requests
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                json_data = json.loads(body.decode("utf-8"))
                await self._validate_json_data(request, json_data)
            elif "application/x-www-form-urlencoded" in content_type:
                # Form data validation could be added here
                pass
            elif "multipart/form-data" in content_type:
                # File upload validation could be added here
                pass

        except json.JSONDecodeError:
            if "application/json" in content_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON in request body",
                )

    async def _validate_json_data(self, request: Request, data: Any) -> None:
        """Validate JSON data for security issues."""
        if not isinstance(data, dict):
            return

        # Recursively validate all string values
        await self._validate_dict_data(request, data)

    async def _validate_dict_data(self, request: Request, data: Dict[str, Any]) -> None:
        """Recursively validate dictionary data."""
        for key, value in data.items():
            if isinstance(value, str):
                await self._validate_string_value(request, key, value)
            elif isinstance(value, dict):
                await self._validate_dict_data(request, value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        await self._validate_dict_data(request, item)
                    elif isinstance(item, str):
                        await self._validate_string_value(request, key, item)

    async def _validate_string_value(self, request: Request, key: str, value: str) -> None:
        """Validate individual string values for security threats."""

        # XSS protection
        if self.enable_xss_protection:
            for pattern in self.xss_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    logger.warning(
                        "Potential XSS detected",
                        extra={
                            "field": key,
                            "pattern": pattern,
                            "path": request.url.path,
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Potential security threat detected in field '{key}'",
                    )

        # SQL injection basic checks
        if self.enable_sql_injection_check:
            for pattern in self.sql_injection_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    logger.warning(
                        "Potential SQL injection detected",
                        extra={
                            "field": key,
                            "pattern": pattern,
                            "path": request.url.path,
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Potential security threat detected in field '{key}'",
                    )

    async def _validate_response(self, request: Request, response: Response) -> None:
        """Validate response (optional, can be extended)."""
        # Could add response size limits, content validation, etc.
        pass

    def _log_request(self, request: Request) -> None:
        """Log request details for monitoring."""
        logger.info(
            "Request processed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "user_agent": request.headers.get("user-agent", "unknown"),
                "content_type": request.headers.get("content-type", "none"),
                "content_length": request.headers.get("content-length", "0"),
            },
        )


def setup_validation_middleware(
    app: Any,
    max_request_size: int = 10 * 1024 * 1024,  # 10MB
    allowed_content_types: Optional[List[str]] = None,
    enable_xss_protection: bool = True,
    enable_sql_injection_check: bool = True,
    enable_logging: bool = True,
) -> None:
    """
    Setup validation middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
        max_request_size: Maximum request size in bytes (default: 10MB)
        allowed_content_types: List of allowed content types
        enable_xss_protection: Enable XSS protection
        enable_sql_injection_check: Enable basic SQL injection checks
        enable_logging: Enable request logging
    """
    app.add_middleware(
        ValidationMiddleware,
        max_request_size=max_request_size,
        allowed_content_types=allowed_content_types,
        enable_xss_protection=enable_xss_protection,
        enable_sql_injection_check=enable_sql_injection_check,
        enable_logging=enable_logging,
    )

    logger.info("Validation middleware setup completed")