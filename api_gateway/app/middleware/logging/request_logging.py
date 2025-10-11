"""
Production-grade HTTP request logging middleware for API Gateway.

This module provides comprehensive HTTP request/response lifecycle logging optimized
for production API Gateway environments. It implements Layer 1 (HTTP-level) logging
that captures essential metrics, user context, and performance data with minimal overhead.

Key Features:
- Unique request ID generation for individual request tracking
- Cross-service correlation ID management for distributed tracing
- Advanced client IP detection (handles load balancers and proxies)
- Performance timing with intelligent log level selection
- User authentication context extraction
- Response header injection for distributed tracing
- Comprehensive error logging with stack traces
- Production-optimized performance (~2-5ms overhead)

Architecture:
This middleware operates as Layer 1 in a dual-layer logging system:
- Layer 1 (request_logging.py): HTTP request/response lifecycle - ALWAYS ACTIVE
- Layer 2 (logging_middleware.py): Route-level debugging - DEBUG MODE ONLY
"""

import time
import uuid
from typing import TYPE_CHECKING, Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from fastapi import FastAPI

from app.utils.logging import setup_api_gateway_logging

logger = setup_api_gateway_logging("api_gateway_request_logging")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Production-grade HTTP request logging middleware for API Gateway"""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())

        # Extract user context (if available from auth)
        user_id = getattr(request.state, "user_id", "anonymous")

        # Establish correlation ID for distributed tracing
        correlation_id = (
            request.headers.get("X-Correlation-ID")
            or getattr(request.state, "correlation_id", None)
            or str(uuid.uuid4())
        )

        # Start timing
        start_time = time.time()

        # Advanced client IP detection
        client_ip = self._get_client_ip(request)

        # Log incoming request with enhanced context
        logger.info(
            "API Gateway HTTP request started",
            extra={
                "request_id": request_id,
                "correlation_id": correlation_id,
                "user_id": user_id,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "user_agent": request.headers.get("user-agent", "unknown")[:200],
                "client_ip": client_ip,
                "event_type": "http_request_start",
                "service": "api_gateway",
                "request_size": request.headers.get("content-length", 0),
            },
        )

        # Store request context
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        request.state.start_time = start_time

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = round((time.time() - start_time) * 1000, 2)

            # Intelligent log level selection
            if response.status_code >= 500:
                log_level = "ERROR"
            elif response.status_code >= 400:
                log_level = "WARNING"
            elif duration_ms > 5000:
                log_level = "WARNING"
            else:
                log_level = "INFO"

            # Log response with appropriate level
            getattr(logger, log_level.lower())(
                "API Gateway HTTP request completed",
                extra={
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "user_id": user_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "response_size": response.headers.get("content-length", 0),
                    "event_type": "http_request_complete",
                    "service": "api_gateway",
                    "success": response.status_code < 400,
                    "slow_request": duration_ms > 1000,
                },
            )

            # Add tracing headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id

            return response

        except Exception as e:
            # Calculate duration for failed requests
            duration_ms = round((time.time() - start_time) * 1000, 2)

            # Log request failure with full context
            logger.error(
                f"API Gateway HTTP request failed: {str(e)}",
                extra={
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "user_id": user_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "event_type": "http_request_error",
                    "service": "api_gateway",
                },
                exc_info=True,
            )

            # Re-raise the exception
            raise

    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP with advanced detection for production environments"""
        # Check X-Forwarded-For header (most common)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header (common with NGINX)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host

        return "unknown"


def setup_api_gateway_request_logging(app: "FastAPI") -> None:
    """Setup production-grade request logging middleware for API Gateway"""
    app.add_middleware(RequestLoggingMiddleware)
    logger.info(
        "API Gateway request logging middleware configured",
        extra={
            "event_type": "middleware_setup",
            "service": "api_gateway",
            "middleware": "request_logging",
        },
    )
