import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from user_service.app.utils.logging import setup_user_logging

logger = setup_user_logging("user_service_error_handler")


class UserServiceErrorHandler:
    """Class to setup error handling middleware for the User Service."""

    @staticmethod
    def setup_error_handlers(app: FastAPI) -> None:
        """Setup error handlers for the FastAPI application."""

        @app.exception_handler(StarletteHTTPException)
        async def http_exception_handler(  # type: ignore
            request: Request, exc: StarletteHTTPException
        ) -> JSONResponse:
            """Handle HTTP exceptions."""

            return UserServiceErrorHandler._create_error_response(
                request=request,
                status_code=exc.status_code,
                error_type="http_error",
                message=str(exc.detail),
                details={"path": request.url.path, "method": request.method},
            )

        @app.exception_handler(RequestValidationError)
        async def validation_exception_handler(  # type: ignore
            request: Request, exc: RequestValidationError
        ) -> JSONResponse:
            """Handle request validation errors."""

            error_details: list[dict[str, str]] = []
            for error in exc.errors():
                error_details.append(
                    {
                        "field": ".".join(str(loc) for loc in error["loc"]),
                        "message": error["msg"],
                        "type": error["type"],
                    }
                )

            return UserServiceErrorHandler._create_error_response(
                request=request,
                status_code=422,
                error_type="validation_error",
                message="Request validation failed",
                details={
                    "validation_errors": error_details,
                    "path": request.url.path,
                    "method": request.method,
                },
            )

        @app.exception_handler(ValidationError)
        async def pydantic_validation_exception_handler(  # type: ignore
            request: Request, exc: ValidationError
        ) -> JSONResponse:
            """Handle Pydantic validation errors."""

            error_details: list[dict[str, str]] = []
            for error in exc.errors():
                error_details.append(
                    {
                        "field": ".".join(str(loc) for loc in error["loc"]),
                        "message": error["msg"],
                        "type": error["type"],
                    }
                )

            return UserServiceErrorHandler._create_error_response(
                request=request,
                status_code=400,
                error_type="data_validation_error",
                message="Data validation failed",
                details={"validation_errors": error_details},
            )

        @app.exception_handler(ValueError)
        async def value_error_handler(  # type: ignore
            request: Request, exc: ValueError
        ) -> JSONResponse:
            """Handle value errors."""

            return UserServiceErrorHandler._create_error_response(
                request=request,
                status_code=400,
                error_type="value_error",
                message=str(exc),
                details={"exception_type": "ValueError"},
            )

        @app.exception_handler(PermissionError)
        async def permission_error_handler(  # type: ignore
            request: Request, exc: PermissionError
        ) -> JSONResponse:
            """Handle permission denied errors."""

            return UserServiceErrorHandler._create_error_response(
                request=request,
                status_code=403,
                error_type="permission_error",
                message="Insufficient permissions",
                details={"exception_type": "PermissionError"},
            )

        @app.exception_handler(Exception)
        async def general_exception_handler(  # type: ignore
            request: Request, exc: Exception
        ) -> JSONResponse:
            """Handle all uncaught exceptions."""

            logger.error(
                "Unhandled exception occurred",
                extra={
                    "correlation_id": getattr(
                        request.state, "correlation_id", "unknown"
                    ),
                    "user_id": getattr(request.state, "user_id", "anonymous"),
                    "path": request.url.path,
                    "method": request.method,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "traceback": traceback.format_exc(),
                    "service": "user_service",
                    "event_type": "unhandled_exception",
                },
                exc_info=True,
            )

            return UserServiceErrorHandler._create_error_response(
                request=request,
                status_code=500,
                error_type="internal_server_error",
                message="An internal server error occurred",
                details={"exception_type": type(exc).__name__},
            )

    @staticmethod
    def _create_error_response(
        request: Request,
        status_code: int,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> JSONResponse:
        """Create a standardized error response."""

        correlation_id = getattr(request.state, "correlation_id", "unknown")
        user_id = getattr(request.state, "user_id", "anonymous")

        error_response: Dict[str, Any] = {
            "error": {
                "type": error_type,
                "message": message,
                "correlation_id": correlation_id,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": request.url.path,
                "method": request.method,
            }
        }

        if details:
            error_response["error"]["details"] = details

        if status_code < 500:
            logger.warning(
                f"Client error: {error_type}",
                extra={
                    "correlation_id": correlation_id,
                    "user_id": user_id,
                    "status_code": status_code,
                    "error_type": error_type,
                    "path": request.url.path,
                    "method": request.method,
                    "service": "user_service",
                    "event_type": "client_error",
                },
            )

        return JSONResponse(status_code=status_code, content=error_response)


def setup_user_error_handling(app: FastAPI) -> None:
    """Setup error handling middleware for the User Service."""

    error_handler = UserServiceErrorHandler()
    error_handler.setup_error_handlers(app)

    logger.info(
        "User Service error handling configured",
        extra={"service": "user_service", "event_type": "error_handler_setup"},
    )
