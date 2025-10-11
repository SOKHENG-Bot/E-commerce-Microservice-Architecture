"""
Request/Response validation middleware for Order Service.
Handles input validation, sanitization, and security checks at middleware level.
"""

import json
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Setup logger
try:
    from order_service.app.utils.logging import setup_order_logging

    logger = setup_order_logging("order_service_validation")
except ImportError:
    logger = logging.getLogger("order_service_validation")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)


class OrderServiceRequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive request validation middleware for Order Service.

    Features:
    - Request size limits with path-specific limits
    - Content type validation
    - Request body validation and sanitization
    - Security header validation
    - Order service specific path handling
    - Request logging and monitoring
    - Correlation ID integration
    """

    def __init__(
        self,
        app: Any,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB default
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
        ]

        # Order Service specific size limits
        self.path_size_limits = {
            "/api/v1/orders": 2 * 1024 * 1024,  # 2MB for order operations
            "/api/v1/orders/bulk": 5 * 1024 * 1024,  # 5MB for bulk order operations
            "/api/v1/payments": 1 * 1024 * 1024,  # 1MB for payment operations
            "/api/v1/shipping": 1 * 1024 * 1024,  # 1MB for shipping operations
            "/api/v1/orders/analytics": 500 * 1024,  # 500KB for analytics queries
        }

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process request validation for each request.
        """
        # Skip validation for excluded paths
        if self._should_skip_validation(request.url.path):
            return await call_next(request)

        # Extract correlation ID
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        try:
            # Validate request size with path-specific limits
            size_validation = await self._validate_request_size(request)
            if not size_validation["valid"]:
                return await self._create_validation_error_response(
                    request, correlation_id, size_validation["error"], 413
                )

            # Validate content type
            content_type_validation = self._validate_content_type(request)
            if not content_type_validation["valid"]:
                return await self._create_validation_error_response(
                    request, correlation_id, content_type_validation["error"], 415
                )

            # Validate required headers
            header_validation = self._validate_required_headers(request)
            if not header_validation["valid"]:
                return await self._create_validation_error_response(
                    request, correlation_id, header_validation["error"], 400
                )

            # Check blocked paths
            if self._is_path_blocked(request.url.path):
                return await self._create_validation_error_response(
                    request, correlation_id, "Path is blocked", 403
                )

            # Validate and sanitize request body for JSON requests
            if request.method in ["POST", "PUT", "PATCH"] and self._is_json_request(
                request
            ):
                body_validation = await self._validate_request_body(request)
                if not body_validation["valid"]:
                    return await self._create_validation_error_response(
                        request, correlation_id, body_validation["error"], 400
                    )

            # Log successful validation
            logger.info(
                "Request validation successful",
                extra={
                    "correlation_id": correlation_id,
                    "path": request.url.path,
                    "method": request.method,
                    "content_type": request.headers.get("content-type", "unknown"),
                    "content_length": request.headers.get("content-length", "unknown"),
                    "user_agent": request.headers.get("user-agent", "unknown"),
                    "service": "order_service",
                    "event_type": "validation_success",
                },
            )

            # Process the request
            response = await call_next(request)
            return response

        except Exception as e:
            # Unexpected validation error
            logger.error(
                f"Request validation error: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(e),
                    "service": "order_service",
                    "event_type": "validation_error",
                },
                exc_info=True,
            )

            # Return 400 for validation errors
            from fastapi.responses import JSONResponse

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
        """
        Check if validation should be skipped for this path.
        """
        # Check exact matches
        if path in self.exclude_paths:
            return True

        # Check prefix matches
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True

        return False

    def _is_path_blocked(self, path: str) -> bool:
        """
        Check if the path is blocked.
        """
        for blocked_path in self.blocked_paths:
            if path.startswith(blocked_path):
                return True
        return False

    def _get_path_size_limit(self, path: str) -> int:
        """
        Get size limit for specific path.
        """
        # Check exact path matches
        if path in self.path_size_limits:
            return self.path_size_limits[path]

        # Check prefix matches
        for limit_path, limit in self.path_size_limits.items():
            if path.startswith(limit_path):
                return limit

        return self.max_request_size

    async def _validate_request_size(self, request: Request) -> Dict[str, Any]:
        """
        Validate request size against path-specific limits.
        """
        try:
            path_limit = self._get_path_size_limit(request.url.path)

            # Check Content-Length header first
            content_length = request.headers.get("content-length")
            if content_length:
                size = int(content_length)
                if size > path_limit:
                    return {
                        "valid": False,
                        "error": f"Request size {size} exceeds limit {path_limit} for path {request.url.path}",
                    }

            # For requests with body, check actual size
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
        """
        Validate request content type.
        """
        content_type = request.headers.get("content-type", "").lower()

        # Allow requests without content-type for GET/HEAD/DELETE
        if request.method in ["GET", "HEAD", "DELETE"]:
            return {"valid": True}

        # Check if content-type is allowed
        if content_type:
            # Check exact matches
            if content_type in self.allowed_content_types:
                return {"valid": True}

            # Check prefix matches (for charset, etc.)
            for allowed_type in self.allowed_content_types:
                if content_type.startswith(allowed_type):
                    return {"valid": True}

        return {
            "valid": False,
            "error": f"Content-Type '{content_type}' is not allowed. Allowed types: {self.allowed_content_types}",
        }

    def _validate_required_headers(self, request: Request) -> Dict[str, Any]:
        """
        Validate required headers are present.
        """
        missing_headers: List[str] = []
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
        """
        Check if request is JSON.
        """
        content_type = request.headers.get("content-type", "").lower()
        return "application/json" in content_type

    async def _validate_request_body(self, request: Request) -> Dict[str, Any]:
        """
        Validate and sanitize JSON request body.
        """
        try:
            # Read body
            body = await request.body()

            if not body:
                return {"valid": True}

            # Parse JSON
            try:
                data = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as e:
                return {
                    "valid": False,
                    "error": f"Invalid JSON: {str(e)}",
                }

            # Order service specific validation
            validation_result = self._validate_order_service_data(
                data, request.url.path
            )
            if not validation_result["valid"]:
                return validation_result

            # Basic security checks
            security_result = self._validate_json_security(data)
            if not security_result["valid"]:
                return security_result

            # Store sanitized data in request state for endpoints to use
            request.state.validated_body = data

            return {"valid": True}

        except Exception as e:
            return {
                "valid": False,
                "error": f"Body validation failed: {str(e)}",
            }

    def _validate_order_service_data(self, data: Any, path: str) -> Dict[str, Any]:
        """
        Perform order service specific data validation.
        """
        try:
            # Validate order creation data
            if path == "/api/v1/orders":
                return self._validate_order_creation_data(data)
            # Validate order update data
            elif path.startswith("/api/v1/orders/") and isinstance(data, dict):
                return self._validate_order_update_data(data)
            # Validate payment data
            elif path.startswith("/api/v1/payments/") and isinstance(data, dict):
                return self._validate_payment_data(data)
            # Validate shipping data
            elif path.startswith("/api/v1/shipping/") and isinstance(data, dict):
                return self._validate_shipping_data(data)

            return {"valid": True}

        except Exception as e:
            return {
                "valid": False,
                "error": f"Order service data validation failed: {str(e)}",
            }

    def _validate_order_creation_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate order creation data.
        """
        required_fields = ["items", "total_amount"]
        for field in required_fields:
            if field not in data:
                return {
                    "valid": False,
                    "error": f"Missing required field: {field}",
                }

        # Validate items array
        items = data.get("items", [])
        if not isinstance(items, list) or len(items) == 0:
            return {
                "valid": False,
                "error": "Items must be a non-empty array",
            }

        # Validate each item
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                return {
                    "valid": False,
                    "error": f"Item {i} must be an object",
                }
            if "product_id" not in item or "quantity" not in item:
                return {
                    "valid": False,
                    "error": f"Item {i} missing required fields: product_id, quantity",
                }
            if not isinstance(item["quantity"], int) or item["quantity"] <= 0:
                return {
                    "valid": False,
                    "error": f"Item {i} quantity must be a positive integer",
                }

        # Validate total amount
        total_amount = data.get("total_amount", 0)
        if not isinstance(total_amount, (int, float)) or total_amount <= 0:
            return {
                "valid": False,
                "error": "Total amount must be a positive number",
            }

        return {"valid": True}

    def _validate_order_update_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate order update data.
        """
        # Check for dangerous fields that shouldn't be updated directly
        dangerous_fields = ["id", "user_id", "created_at", "updated_at", "total_amount"]
        for field in dangerous_fields:
            if field in data:
                return {
                    "valid": False,
                    "error": f"Field '{field}' cannot be updated directly",
                }

        # Validate status if provided
        if "status" in data:
            valid_statuses = [
                "pending",
                "confirmed",
                "processing",
                "shipped",
                "delivered",
                "cancelled",
            ]
            if data["status"] not in valid_statuses:
                return {
                    "valid": False,
                    "error": f"Invalid status. Must be one of: {valid_statuses}",
                }

        return {"valid": True}

    def _validate_payment_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate payment data.
        """
        required_fields = ["order_id", "amount", "payment_method"]
        for field in required_fields:
            if field not in data:
                return {
                    "valid": False,
                    "error": f"Missing required field: {field}",
                }

        # Validate amount
        amount = data.get("amount", 0)
        if not isinstance(amount, (int, float)) or amount <= 0:
            return {
                "valid": False,
                "error": "Amount must be a positive number",
            }

        # Validate payment method
        valid_methods = ["credit_card", "debit_card", "paypal", "bank_transfer", "cash"]
        if data.get("payment_method") not in valid_methods:
            return {
                "valid": False,
                "error": f"Invalid payment method. Must be one of: {valid_methods}",
            }

        return {"valid": True}

    def _validate_shipping_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate shipping data.
        """
        required_fields = ["order_id", "address", "carrier"]
        for field in required_fields:
            if field not in data:
                return {
                    "valid": False,
                    "error": f"Missing required field: {field}",
                }

        # Validate address structure
        address = data.get("address", {})
        if not isinstance(address, dict):
            return {
                "valid": False,
                "error": "Address must be an object",
            }

        address_required = ["street", "city", "country", "postal_code"]
        for field in address_required:
            if field not in address:
                return {
                    "valid": False,
                    "error": f"Missing required address field: {field}",
                }

        return {"valid": True}

    def _validate_json_security(self, data: Any) -> Dict[str, Any]:
        """
        Perform security validation on JSON data.
        """
        # Check for nested objects depth (prevent deep recursion)
        max_depth = 10
        if self._get_json_depth(data) > max_depth:
            return {
                "valid": False,
                "error": f"JSON object too deeply nested (max depth: {max_depth})",
            }

        # Check for extremely large arrays
        max_array_size = 1000
        if self._has_large_array(data, max_array_size):
            return {
                "valid": False,
                "error": f"JSON contains array larger than {max_array_size} elements",
            }

        # Check for potentially dangerous keys
        dangerous_keys = ["__proto__", "constructor", "prototype"]
        if self._has_dangerous_keys(data, dangerous_keys):
            return {
                "valid": False,
                "error": "JSON contains potentially dangerous keys",
            }

        return {"valid": True}

    def _get_json_depth(self, obj: Any, current_depth: int = 0) -> int:
        """
        Calculate JSON object depth.
        """
        if current_depth > 20:  # Safety limit
            return current_depth

        if isinstance(obj, dict):
            return max(
                (self._get_json_depth(v, current_depth + 1) for v in obj.values()),
                default=current_depth,
            )
        elif isinstance(obj, list):
            return max(
                (self._get_json_depth(item, current_depth + 1) for item in obj),
                default=current_depth,
            )
        else:
            return current_depth

    def _has_large_array(self, obj: Any, max_size: int) -> bool:
        """
        Check if JSON contains arrays that are too large.
        """
        if isinstance(obj, list) and len(obj) > max_size:
            return True
        elif isinstance(obj, dict):
            return any(self._has_large_array(v, max_size) for v in obj.values())
        return False

    def _has_dangerous_keys(self, obj: Any, dangerous_keys: List[str]) -> bool:
        """
        Check for dangerous keys in JSON.
        """
        if isinstance(obj, dict):
            for key in obj.keys():
                if isinstance(key, str) and key.lower() in dangerous_keys:
                    return True
                if self._has_dangerous_keys(obj[key], dangerous_keys):
                    return True
        elif isinstance(obj, list):
            return any(self._has_dangerous_keys(item, dangerous_keys) for item in obj)
        return False

    async def _create_validation_error_response(
        self,
        request: Request,
        correlation_id: str,
        error_message: str,
        status_code: int,
    ) -> Response:
        """
        Create a standardized validation error response.
        """
        # Log validation failure
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
                "service": "order_service",
                "event_type": "validation_failed",
            },
        )

        from fastapi.responses import JSONResponse

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


def setup_order_request_validation_middleware(
    app: FastAPI,
    max_request_size: int = 10 * 1024 * 1024,  # 10MB
    allowed_content_types: Optional[List[str]] = None,
    required_headers: Optional[List[str]] = None,
    blocked_paths: Optional[List[str]] = None,
    exclude_paths: Optional[List[str]] = None,
) -> None:
    """
    Setup request validation middleware for Order Service.

    Args:
        app: FastAPI application instance
        max_request_size: Maximum request size in bytes
        allowed_content_types: List of allowed content types
        required_headers: List of required headers
        blocked_paths: List of blocked path patterns
        exclude_paths: List of paths to exclude from validation

    Example:
        setup_order_request_validation_middleware(
            app,
            max_request_size=5 * 1024 * 1024,  # 5MB
            allowed_content_types=["application/json"],
            required_headers=["Authorization"],
            blocked_paths=["/admin/debug"],
        )
    """
    if exclude_paths is None:
        exclude_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        ]

    if blocked_paths is None:
        blocked_paths = ["/.env", "/.git", "/admin/debug"]

    app.add_middleware(
        OrderServiceRequestValidationMiddleware,
        max_request_size=max_request_size,
        allowed_content_types=allowed_content_types,
        required_headers=required_headers,
        blocked_paths=blocked_paths,
        exclude_paths=exclude_paths,
    )

    logger.info(
        "Request validation middleware configured",
        extra={
            "service": "order_service",
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
