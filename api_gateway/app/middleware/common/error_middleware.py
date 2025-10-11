"""
Error handling middleware for API Gateway.
Provides centralized exception management and standardized error responses.
"""

import traceback
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.utils.logging import setup_api_gateway_logging

logger = setup_api_gateway_logging("api_gateway_error_middleware")


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware that catches exceptions and returns standardized error responses.

    Features:
    - Global exception catching
    - Standardized error response format
    - Detailed logging for debugging
    - Different error levels for production vs development
    - Custom error codes and messages
    - API Gateway specific error handling
    """

    def __init__(
        self,
        app: Any,
        debug_mode: bool = False,
        include_traceback: bool = False,
        custom_error_handlers: Optional[
            Dict[type, Callable[[Request, Exception], Any]]
        ] = None,
    ):
        super().__init__(app)
        self.debug_mode = debug_mode
        self.include_traceback = include_traceback
        self.custom_error_handlers = custom_error_handlers or {}

        logger.info(
            "API Gateway error handling middleware initialized",
            extra={
                "debug_mode": debug_mode,
                "include_traceback": include_traceback,
                "custom_handlers_count": len(custom_error_handlers or {}),
            },
        )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process each request and handle any exceptions."""
        try:
            # Process the request
            response = await call_next(request)
            return response

        except Exception as exc:
            # Handle the exception
            return await self._handle_exception(request, exc)

    async def _handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle exceptions and return appropriate error responses."""

        # Check for custom error handlers first
        if type(exc) in self.custom_error_handlers:
            return await self.custom_error_handlers[type(exc)](request, exc)

        # Handle HTTPException (FastAPI's built-in exceptions)
        if isinstance(exc, HTTPException):
            return await self._handle_http_exception(request, exc)

        # Handle other exceptions
        return await self._handle_generic_exception(request, exc)

    async def _handle_http_exception(
        self, request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Handle FastAPI HTTPException with standardized format."""

        error_response = {
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "type": "http_exception",
                "status_code": exc.status_code,
            },
            "request": {
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
            },
        }

        # Add debug information if in debug mode
        if self.debug_mode:
            error_response["debug"] = {
                "headers": dict(request.headers),
                "query_params": dict(request.query_params),
            }

        # Log the HTTP exception
        logger.warning(
            "HTTP exception occurred",
            extra={
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": request.url.path,
                "method": request.method,
                "user_agent": request.headers.get("user-agent", "unknown"),
                "correlation_id": getattr(request.state, "correlation_id", "unknown"),
                "user_id": getattr(request.state, "user_id", "anonymous"),
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
        )

    async def _handle_generic_exception(
        self, request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle generic exceptions with error details."""

        # Get exception details
        exc_type = type(exc).__name__
        exc_message = str(exc)
        exc_traceback = traceback.format_exc() if self.include_traceback else None

        # Determine status code based on exception type
        status_code = await self._get_status_code_for_exception(exc)

        error_response = {
            "error": {
                "code": f"INTERNAL_ERROR_{exc_type.upper()}",
                "message": exc_message
                if self.debug_mode
                else "An internal error occurred",
                "type": "internal_error",
                "status_code": status_code,
            },
            "request": {
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
            },
        }

        # Add correlation ID and user ID
        error_response["error"]["correlation_id"] = getattr(
            request.state, "correlation_id", "unknown"
        )
        error_response["error"]["user_id"] = getattr(
            request.state, "user_id", "anonymous"
        )

        # Add traceback in debug mode
        if self.debug_mode and exc_traceback:
            error_response["debug"] = {
                "traceback": exc_traceback,
                "exception_type": exc_type,
            }

        # Log the error with full details
        logger.error(
            "Unhandled exception occurred",
            exc_info=True,
            extra={
                "exception_type": exc_type,
                "exception_message": exc_message,
                "status_code": status_code,
                "path": request.url.path,
                "method": request.method,
                "user_agent": request.headers.get("user-agent", "unknown"),
                "correlation_id": getattr(request.state, "correlation_id", "unknown"),
                "user_id": getattr(request.state, "user_id", "anonymous"),
                "traceback": exc_traceback
                if self.include_traceback
                else "not included",
            },
        )

        return JSONResponse(
            status_code=status_code,
            content=error_response,
        )

    async def _get_status_code_for_exception(self, exc: Exception) -> int:
        """Determine appropriate HTTP status code for different exception types."""

        exc_str = str(type(exc)).lower()
        exc_msg = str(exc).lower()

        # Database-related exceptions
        if "database" in exc_str or "sql" in exc_str or "psycopg" in exc_str:
            return status.HTTP_503_SERVICE_UNAVAILABLE

        # Connection/network errors
        if "connection" in exc_msg or "network" in exc_msg or "timeout" in exc_msg:
            return status.HTTP_503_SERVICE_UNAVAILABLE

        # Authentication/Authorization errors
        if "auth" in exc_msg or "token" in exc_msg or "permission" in exc_msg:
            return status.HTTP_401_UNAUTHORIZED

        # Service unavailable (other services down)
        if "service" in exc_msg and "unavailable" in exc_msg:
            return status.HTTP_503_SERVICE_UNAVAILABLE

        # Rate limiting
        if "rate" in exc_msg and "limit" in exc_msg:
            return status.HTTP_429_TOO_MANY_REQUESTS

        # Validation errors
        if "validation" in exc_msg or "pydantic" in exc_str:
            return status.HTTP_422_UNPROCESSABLE_ENTITY

        # File system errors
        if "file" in exc_msg or "io" in exc_str:
            return status.HTTP_500_INTERNAL_SERVER_ERROR

        # Default to 500 for unknown exceptions
        return status.HTTP_500_INTERNAL_SERVER_ERROR


# Custom error handlers for specific exception types
async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic validation errors."""
    try:
        from pydantic import ValidationError

        if isinstance(exc, ValidationError):
            error_details = []
            for error in exc.errors():
                error_details.append(
                    {
                        "field": ".".join(str(loc) for loc in error["loc"]),
                        "message": error["msg"],
                        "type": error["type"],
                    }
                )

            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Request validation failed",
                        "type": "validation_error",
                        "status_code": 422,
                        "correlation_id": getattr(
                            request.state, "correlation_id", "unknown"
                        ),
                        "user_id": getattr(request.state, "user_id", "anonymous"),
                        "details": error_details,
                    },
                    "request": {
                        "method": request.method,
                        "url": str(request.url),
                        "path": request.url.path,
                    },
                },
            )
    except ImportError:
        pass

    # Fallback
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc),
                "type": "validation_error",
                "status_code": 422,
                "correlation_id": getattr(request.state, "correlation_id", "unknown"),
                "user_id": getattr(request.state, "user_id", "anonymous"),
            }
        },
    )


async def handle_service_unavailable_error(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle service unavailable errors."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": {
                "code": "SERVICE_UNAVAILABLE",
                "message": "Service temporarily unavailable",
                "type": "service_error",
                "status_code": 503,
                "correlation_id": getattr(request.state, "correlation_id", "unknown"),
                "user_id": getattr(request.state, "user_id", "anonymous"),
            },
            "request": {
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
            },
        },
    )


def setup_error_middleware(
    app: Any,
    debug_mode: bool = False,
    include_traceback: bool = False,
    custom_error_handlers: Optional[
        Dict[type, Callable[[Request, Exception], Any]]
    ] = None,
) -> None:
    """
    Setup error handling middleware for the API Gateway.

    Args:
        app: FastAPI application instance
        debug_mode: Enable detailed error information for debugging
        include_traceback: Include full traceback in error responses (only in debug mode)
        custom_error_handlers: Dictionary of custom error handlers for specific exception types
    """

    # Default custom error handlers
    default_handlers = {
        # Add more custom handlers as needed
    }

    # Merge with provided custom handlers
    if custom_error_handlers:
        default_handlers.update(custom_error_handlers)

    app.add_middleware(
        ErrorHandlingMiddleware,
        debug_mode=debug_mode,
        include_traceback=include_traceback
        and debug_mode,  # Only include traceback in debug mode
        custom_error_handlers=default_handlers,
    )

    logger.info(
        "API Gateway error handling middleware setup completed",
        extra={
            "debug_mode": debug_mode,
            "include_traceback": include_traceback and debug_mode,
            "custom_handlers_count": len(default_handlers),
        },
    )
