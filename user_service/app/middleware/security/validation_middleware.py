import json
from typing import Any, Awaitable, Callable, Dict, List, Optional, cast

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from user_service.app.utils.logging import setup_user_logging

logger = setup_user_logging("user_service_validation")


class UserServiceRequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware to validate incoming requests for the User Service."""

    def __init__(
        self,
        app: Any,
        max_request_size: int = 10 * 1024 * 1024,
        allowed_content_types: Optional[List[str]] = None,
        required_headers: Optional[List[str]] = None,
        blocked_paths: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.max_request_size = max_request_size
        self.allowed_content_types = allowed_content_types or [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/plain",
        ]
        self.required_headers = required_headers or []
        self.blocked_paths = blocked_paths or []
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
        ]
        self.path_size_limits = {
            "/api/v1/users/avatar": 5 * 1024 * 1024,
            "/api/v1/profiles/avatar": 5 * 1024 * 1024,
            "/api/v1/users": 1 * 1024 * 1024,
            "/api/v1/profiles": 1 * 1024 * 1024,
            "/api/v1/auth/register": 100 * 1024,
            "/api/v1/auth/login": 50 * 1024,
            "/api/v1/addresses": 500 * 1024,
            "/api/v1/bulk": 2 * 1024 * 1024,
        }

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Middleware to validate incoming requests for the User Service."""

        if self._should_skip_validation(request.url.path):
            return await call_next(request)

        correlation_id = getattr(request.state, "correlation_id", "unknown")
        try:
            size_validation = await self._validate_request_size(request)
            if not size_validation["valid"]:
                return await self._create_validation_error_response(
                    request, correlation_id, size_validation["error"], 413
                )

            content_type_validation = self._validate_content_type(request)
            if not content_type_validation["valid"]:
                return await self._create_validation_error_response(
                    request, correlation_id, content_type_validation["error"], 415
                )

            header_validation = self._validate_required_headers(request)
            if not header_validation["valid"]:
                return await self._create_validation_error_response(
                    request, correlation_id, header_validation["error"], 400
                )

            if self._is_path_blocked(request.url.path):
                return await self._create_validation_error_response(
                    request, correlation_id, "Path is blocked", 403
                )

            if request.method in ["POST", "PUT", "PATCH"] and self._is_json_request(
                request
            ):
                body_validation = await self._validate_request_body(request)
                if not body_validation["valid"]:
                    return await self._create_validation_error_response(
                        request, correlation_id, body_validation["error"], 400
                    )

            logger.info(
                "Request validation successful",
                extra={
                    "correlation_id": correlation_id,
                    "path": request.url.path,
                    "method": request.method,
                    "content_type": request.headers.get("content-type", "unknown"),
                    "content_length": request.headers.get("content-length", "unknown"),
                    "user_agent": request.headers.get("user-agent", "unknown"),
                    "service": "user_service",
                    "event_type": "validation_success",
                },
            )
            response = await call_next(request)
            return response

        except Exception as e:
            logger.error(
                f"Request validation error: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(e),
                    "service": "user_service",
                    "event_type": "validation_error",
                },
                exc_info=True,
            )

            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "type": "validation_error",
                        "message": "Request validation failed",
                        "correlation_id": correlation_id,
                        "details": {"error": str(e)},
                    }
                },
            )

    def _should_skip_validation(self, path: str) -> bool:
        """Check if validation should be skipped for this path."""

        if path in self.exclude_paths:
            return True

        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False

    def _is_path_blocked(self, path: str) -> bool:
        """Check if the path is blocked."""

        for blocked_path in self.blocked_paths:
            if path.startswith(blocked_path):
                return True
        return False

    def _get_path_size_limit(self, path: str) -> int:
        """Get size limit for specific path."""

        if path in self.path_size_limits:
            return self.path_size_limits[path]

        for limit_path, limit in self.path_size_limits.items():
            if path.startswith(limit_path):
                return limit
        return self.max_request_size

    async def _validate_request_size(self, request: Request) -> Dict[str, Any]:
        """Validate request size against path-specific limits."""

        try:
            path_limit = self._get_path_size_limit(request.url.path)

            content_length = request.headers.get("content-length")
            if content_length:
                size = int(content_length)
                if size > path_limit:
                    return {
                        "valid": False,
                        "error": f"Request size {size} exceeds limit {path_limit} for path {request.url.path}",
                    }

            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if len(body) > path_limit:
                    return {
                        "valid": False,
                        "error": f"Request body size {len(body)} exceeds limit {path_limit} for path {request.url.path}",
                    }

            return {"valid": True}
        except Exception as e:
            return {
                "valid": False,
                "error": f"Failed to validate request size: {str(e)}",
            }

    def _validate_content_type(self, request: Request) -> Dict[str, Any]:
        """Validate Content-Type header."""

        content_type = request.headers.get("content-type", "").lower()

        if request.method in ["GET", "HEAD", "DELETE"]:
            return {"valid": True}

        if request.url.path in ["/api/v1/users/avatar", "/api/v1/profiles/avatar"]:
            if "multipart/form-data" in content_type:
                return {"valid": True}

        if content_type:
            if content_type in self.allowed_content_types:
                return {"valid": True}

            for allowed_type in self.allowed_content_types:
                if content_type.startswith(allowed_type):
                    return {"valid": True}
        return {
            "valid": False,
            "error": f"Content-Type '{content_type}' is not allowed. Allowed types: {self.allowed_content_types}",
        }

    def _validate_required_headers(self, request: Request) -> Dict[str, Any]:
        """Validate presence of required headers."""

        missing_headers: list[str] = []
        for header in self.required_headers:
            if header.lower() not in [h.lower() for h in request.headers.keys()]:
                missing_headers.append(header)

        if missing_headers:
            return {
                "valid": False,
                "error": f"Missing required headers: {missing_headers}",
            }
        return {"valid": True}

    def _is_json_request(self, request: Request) -> bool:
        """Check if request is JSON based on Content-Type header."""

        content_type = request.headers.get("content-type", "").lower()
        return "application/json" in content_type

    async def _validate_request_body(self, request: Request) -> Dict[str, Any]:
        """Validate JSON request body for User Service specific rules."""

        try:
            body = await request.body()

            if not body:
                return {"valid": True}

            try:
                data = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as e:
                return {
                    "valid": False,
                    "error": f"Invalid JSON: {str(e)}",
                }

            validation_result = self._validate_user_service_data(data, request.url.path)
            if not validation_result["valid"]:
                return validation_result

            security_result = self._validate_json_security(data)
            if not security_result["valid"]:
                return security_result

            request.state.validated_body = data

            return {"valid": True}

        except Exception as e:
            return {
                "valid": False,
                "error": f"Body validation failed: {str(e)}",
            }

    def _validate_user_service_data(
        self, data: Dict[str, Any], path: str
    ) -> Dict[str, Any]:
        """Perform user service specific data validation."""

        try:
            if path == "/api/v1/auth/register":
                return self._validate_registration_data(data)

            elif path.startswith("/api/v1/users/"):
                return self._validate_user_update_data(data)

            elif path.startswith("/api/v1/profiles/"):
                return self._validate_profile_data(data)

            elif path.startswith("/api/v1/addresses/"):
                return self._validate_address_data(data)

            return {"valid": True}

        except Exception as e:
            return {
                "valid": False,
                "error": f"User service data validation failed: {str(e)}",
            }

    def _validate_registration_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user registration data."""

        required_fields = ["email", "password"]
        for field in required_fields:
            if field not in data:
                return {
                    "valid": False,
                    "error": f"Missing required field: {field}",
                }

        email = data.get("email", "")
        if "@" not in email or "." not in email:
            return {
                "valid": False,
                "error": "Invalid email format",
            }

        password = data.get("password", "")
        if len(password) < 8:
            return {
                "valid": False,
                "error": "Password must be at least 8 characters long",
            }
        return {"valid": True}

    def _validate_user_update_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user update data."""

        dangerous_fields = ["id", "created_at", "updated_at", "is_active", "role"]
        for field in dangerous_fields:
            if field in data:
                return {
                    "valid": False,
                    "error": f"Field '{field}' cannot be updated directly",
                }
        return {"valid": True}

    def _validate_profile_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate profile data."""

        if "phone" in data:
            phone = data["phone"]
            if (
                not isinstance(phone, str)
                or not phone.replace("+", "")
                .replace("-", "")
                .replace(" ", "")
                .isdigit()
            ):
                return {
                    "valid": False,
                    "error": "Invalid phone number format",
                }
        return {"valid": True}

    def _validate_address_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate address data."""

        required_fields = ["street", "city", "country", "postal_code"]
        for field in required_fields:
            if field not in data:
                return {
                    "valid": False,
                    "error": f"Missing required address field: {field}",
                }
        return {"valid": True}

    def _validate_json_security(self, data: Any) -> Dict[str, Any]:
        """Perform security checks on JSON data."""

        max_depth = 10
        if self._get_json_depth(data) > max_depth:
            return {
                "valid": False,
                "error": f"JSON object too deeply nested (max depth: {max_depth})",
            }

        max_array_size = 1000
        if self._has_large_array(data, max_array_size):
            return {
                "valid": False,
                "error": f"JSON contains array larger than {max_array_size} elements",
            }

        dangerous_keys = ["__proto__", "constructor", "prototype"]
        if self._has_dangerous_keys(data, dangerous_keys):
            return {
                "valid": False,
                "error": "JSON contains potentially dangerous keys",
            }
        return {"valid": True}

    def _get_json_depth(self, obj: Any, current_depth: int = 0) -> int:
        """Calculate the depth of a JSON object."""

        if current_depth > 20:
            return current_depth

        if isinstance(obj, dict):
            return max(
                (
                    self._get_json_depth(cast(Any, v), current_depth + 1)
                    for v in obj.values()  # type: ignore
                ),
                default=current_depth,
            )
        elif isinstance(obj, list):
            return max(
                (
                    self._get_json_depth(cast(Any, item), current_depth + 1)
                    for item in obj  # type: ignore
                ),
                default=current_depth,
            )
        else:
            return current_depth

    def _has_large_array(self, obj: Any, max_size: int) -> bool:
        """Check for large arrays in JSON."""

        if isinstance(obj, list):
            if len(cast(List[Any], obj)) > max_size:
                return True
        elif isinstance(obj, dict):
            return any(self._has_large_array(v, max_size) for v in obj.values())  # type: ignore
        return False

    def _has_dangerous_keys(self, obj: Any, dangerous_keys: List[str]) -> bool:
        """Check for dangerous keys in JSON."""

        if isinstance(obj, dict):
            for key in obj.keys():  # type: ignore
                if isinstance(key, str) and key.lower() in dangerous_keys:
                    return True
                if self._has_dangerous_keys(obj[key], dangerous_keys):
                    return True
        elif isinstance(obj, list):
            return any(self._has_dangerous_keys(item, dangerous_keys) for item in obj)  # type: ignore
        return False

    async def _create_validation_error_response(
        self,
        request: Request,
        correlation_id: str,
        error_message: str,
        status_code: int,
    ) -> Response:
        """Create a standardized validation error response."""

        logger.warning(
            f"Request validation failed: {error_message}",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": status_code,
                "error": error_message,
                "content_type": request.headers.get("content-type", "unknown"),
                "content_length": request.headers.get("content-length", "unknown"),
                "user_agent": request.headers.get("user-agent", "unknown"),
                "service": "user_service",
                "event_type": "validation_failed",
            },
        )
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "type": "validation_error",
                    "message": error_message,
                    "correlation_id": correlation_id,
                    "details": {
                        "path": request.url.path,
                        "method": request.method,
                    },
                }
            },
        )


def setup_user_request_validation_middleware(
    app: FastAPI,
    max_request_size: int = 10 * 1024 * 1024,
    allowed_content_types: Optional[List[str]] = None,
    required_headers: Optional[List[str]] = None,
    blocked_paths: Optional[List[str]] = None,
    exclude_paths: Optional[List[str]] = None,
) -> None:
    """Setup request validation middleware for the User Service."""

    if exclude_paths is None:
        exclude_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
        ]

    if blocked_paths is None:
        blocked_paths = ["/.env", "/.git", "/admin/debug"]

    app.add_middleware(
        UserServiceRequestValidationMiddleware,
        max_request_size=max_request_size,
        allowed_content_types=allowed_content_types,
        required_headers=required_headers,
        blocked_paths=blocked_paths,
        exclude_paths=exclude_paths,
    )

    logger.info(
        "Request validation middleware configured",
        extra={
            "service": "user_service",
            "max_request_size_mb": max_request_size / (1024 * 1024),
            "allowed_content_types": allowed_content_types
            or [
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
                "text/plain",
            ],
            "required_headers": required_headers or [],
            "blocked_paths": blocked_paths,
            "excluded_paths": exclude_paths,
            "event_type": "validation_middleware_setup",
        },
    )
