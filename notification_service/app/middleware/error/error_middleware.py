"""
Error handling middleware for global exception management and standardized error responses.
"""

import traceback
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ...utils.logging import setup_notification_logging

logger = setup_notification_logging("error_middleware")


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware that catches exceptions and returns standardized error responses.

    Features:
    - Global exception catching
    - Standardized error response format
    - Detailed logging for debugging
    - Different error levels for production vs development
    - Custom error codes and messages
    """

    def __init__(
        self,
        app: Any,
        debug_mode: bool = False,
        include_traceback: bool = False,
        custom_error_handlers: Optional[Dict[type, callable]] = None,
    ):
        super().__init__(app)
        self.debug_mode = debug_mode
        self.include_traceback = include_traceback
        self.custom_error_handlers = custom_error_handlers or {}

        logger.info(
            "Error handling middleware initialized",
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
                "message": exc_message if self.debug_mode else "An internal error occurred",
                "type": "internal_error",
                "status_code": status_code,
            },
            "request": {
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
            },
        }

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
                "traceback": exc_traceback if self.include_traceback else "not included",
            },
        )

        return JSONResponse(
            status_code=status_code,
            content=error_response,
        )

    async def _get_status_code_for_exception(self, exc: Exception) -> int:
        """Determine appropriate HTTP status code for different exception types."""

        # Database-related exceptions
        if "database" in str(type(exc)).lower() or "sql" in str(type(exc)).lower():
            return status.HTTP_503_SERVICE_UNAVAILABLE

        # Connection/network errors
        if "connection" in str(type(exc)).lower() or "network" in str(type(exc)).lower():
            return status.HTTP_503_SERVICE_UNAVAILABLE

        # Validation errors
        if "validation" in str(type(exc)).lower() or "pydantic" in str(type(exc)).lower():
            return status.HTTP_422_UNPROCESSABLE_ENTITY

        # Authentication/Authorization errors
        if "auth" in str(type(exc)).lower() or "permission" in str(type(exc)).lower():
            return status.HTTP_401_UNAUTHORIZED

        # File system errors
        if "file" in str(type(exc)).lower() or "io" in str(type(exc)).lower():
            return status.HTTP_500_INTERNAL_SERVER_ERROR

        # Default to 500 for unknown exceptions
        return status.HTTP_500_INTERNAL_SERVER_ERROR


# Custom error handlers for specific exception types
async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic validation errors."""
    from pydantic import ValidationError

    if isinstance(exc, ValidationError):
        error_details = []
        for error in exc.errors():
            error_details.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "type": "validation_error",
                    "status_code": 422,
                    "details": error_details,
                },
                "request": {
                    "method": request.method,
                    "url": str(request.url),
                    "path": request.url.path,
                },
            },
        )

    # Fallback
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc),
                "type": "validation_error",
                "status_code": 422,
            }
        },
    )


async def handle_database_error(request: Request, exc: Exception) -> JSONResponse:
    """Handle database-related errors."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": {
                "code": "DATABASE_ERROR",
                "message": "Database service temporarily unavailable",
                "type": "database_error",
                "status_code": 503,
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
    custom_error_handlers: Optional[Dict[type, callable]] = None,
) -> None:
    """
    Setup error handling middleware for the FastAPI application.

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
        include_traceback=include_traceback and debug_mode,  # Only include traceback in debug mode
        custom_error_handlers=default_handlers,
    )

    logger.info(
        "Error handling middleware setup completed",
        extra={
            "debug_mode": debug_mode,
            "include_traceback": include_traceback and debug_mode,
            "custom_handlers_count": len(default_handlers),
        },
    )