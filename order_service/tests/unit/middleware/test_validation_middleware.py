"""
Unit tests for Order Service Request Validation Middleware.
"""

import json
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import Request
from starlette.responses import JSONResponse

from order_service.app.middleware.security.validation_middleware import (
    OrderServiceRequestValidationMiddleware,
    setup_order_request_validation_middleware,
)


class TestOrderServiceRequestValidationMiddleware:
    """Test cases for request validation middleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance for testing."""
        return OrderServiceRequestValidationMiddleware(app=Mock())

    @pytest.fixture
    def middleware_with_custom_limits(self):
        """Create middleware with custom size limits."""
        middleware = OrderServiceRequestValidationMiddleware(
            app=Mock(),
            max_request_size=5 * 1024 * 1024,  # 5MB
        )
        # Override the path_size_limits for testing
        middleware.path_size_limits = {
            "/api/v1/orders": 1 * 1024 * 1024,  # 1MB for orders
        }
        return middleware

    def test_middleware_initialization(self, middleware):
        """Test middleware initializes correctly."""
        assert middleware.app is not None
        assert hasattr(middleware, "dispatch")
        assert middleware.max_request_size == 10 * 1024 * 1024  # 10MB default
        assert middleware.allowed_content_types is not None
        assert middleware.exclude_paths is not None

    def test_should_skip_validation_excluded_path(self, middleware):
        """Test that excluded paths skip validation."""
        assert middleware._should_skip_validation("/health") is True
        assert middleware._should_skip_validation("/docs") is True
        # Note: "/api/v1/orders/health" is not in default exclude_paths
        assert middleware._should_skip_validation("/docs/redoc") is True

    def test_should_skip_validation_normal_path(self, middleware):
        """Test that normal paths don't skip validation."""
        assert middleware._should_skip_validation("/api/v1/orders") is False
        assert middleware._should_skip_validation("/api/v1/payments") is False

    def test_is_path_blocked_not_blocked(self, middleware):
        """Test path blocking for normal paths."""
        assert middleware._is_path_blocked("/api/v1/orders") is False

    def test_is_path_blocked_blocked(self, middleware):
        """Test path blocking for blocked paths."""
        middleware.blocked_paths = ["/admin"]
        assert middleware._is_path_blocked("/admin/debug") is True
        assert middleware._is_path_blocked("/admin") is True

    def test_get_path_size_limit_default(self, middleware):
        """Test getting size limit for paths without specific limits."""
        assert (
            middleware._get_path_size_limit("/api/v1/unknown")
            == middleware.max_request_size
        )

    def test_get_path_size_limit_specific(self, middleware_with_custom_limits):
        """Test getting size limit for paths with specific limits."""
        middleware = middleware_with_custom_limits
        assert middleware._get_path_size_limit("/api/v1/orders") == 1 * 1024 * 1024
        assert (
            middleware._get_path_size_limit("/api/v1/orders/bulk") == 1 * 1024 * 1024
        )  # prefix match
        assert (
            middleware._get_path_size_limit("/api/v1/payments")
            == middleware.max_request_size
        )

    @pytest.mark.asyncio
    async def test_validate_request_size_valid(self, middleware):
        """Test request size validation for valid requests."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"content-length": "1024"}

        result = await middleware._validate_request_size(mock_request)
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_request_size_too_large_header(self, middleware):
        """Test request size validation when Content-Length header exceeds limit."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/orders"
        mock_request.headers = {"content-length": str(middleware.max_request_size + 1)}

        result = await middleware._validate_request_size(mock_request)
        assert result["valid"] is False
        assert "exceeds limit" in result["error"]

    @pytest.mark.asyncio
    async def test_validate_request_size_too_large_body(self, middleware):
        """Test request size validation when actual body exceeds limit."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "POST"
        mock_request.headers = {}

        # Mock the body method to return large data
        large_body = b"x" * (middleware.max_request_size + 1)
        mock_request.body = AsyncMock(return_value=large_body)

        result = await middleware._validate_request_size(mock_request)
        assert result["valid"] is False
        assert "exceeds limit" in result["error"]

    def test_validate_content_type_allowed(self, middleware):
        """Test content type validation for allowed types."""
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.headers = {"content-type": "application/json"}

        result = middleware._validate_content_type(mock_request)
        assert result["valid"] is True

    def test_validate_content_type_not_allowed(self, middleware):
        """Test content type validation for disallowed types."""
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.headers = {"content-type": "text/html"}

        result = middleware._validate_content_type(mock_request)
        assert result["valid"] is False
        assert "not allowed" in result["error"]

    def test_validate_content_type_get_request(self, middleware):
        """Test content type validation for GET requests (no content-type required)."""
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}

        result = middleware._validate_content_type(mock_request)
        assert result["valid"] is True

    def test_validate_required_headers_missing(self, middleware):
        """Test required headers validation when headers are missing."""
        middleware.required_headers = ["Authorization", "X-API-Key"]

        mock_request = Mock(spec=Request)
        mock_request.headers = {}

        result = middleware._validate_required_headers(mock_request)
        assert result["valid"] is False
        assert "Missing required headers" in result["error"]

    def test_validate_required_headers_present(self, middleware):
        """Test required headers validation when headers are present."""
        middleware.required_headers = ["Authorization"]

        mock_request = Mock(spec=Request)
        mock_request.headers = {"authorization": "Bearer token"}

        result = middleware._validate_required_headers(mock_request)
        assert result["valid"] is True

    def test_is_json_request_true(self, middleware):
        """Test JSON request detection."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"content-type": "application/json"}

        assert middleware._is_json_request(mock_request) is True

        mock_request.headers = {"content-type": "application/json; charset=utf-8"}
        assert middleware._is_json_request(mock_request) is True

    def test_is_json_request_false(self, middleware):
        """Test non-JSON request detection."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"content-type": "application/x-www-form-urlencoded"}

        assert middleware._is_json_request(mock_request) is False

    @pytest.mark.asyncio
    async def test_validate_request_body_valid_json(self, middleware):
        """Test request body validation for valid JSON."""
        mock_request = Mock(spec=Request)
        mock_request.body = AsyncMock(return_value=b'{"name": "test"}')

        result = await middleware._validate_request_body(mock_request)
        assert result["valid"] is True
        assert mock_request.state.validated_body == {"name": "test"}

    @pytest.mark.asyncio
    async def test_validate_request_body_invalid_json(self, middleware):
        """Test request body validation for invalid JSON."""
        mock_request = Mock(spec=Request)
        mock_request.body = AsyncMock(return_value=b"invalid json")

        result = await middleware._validate_request_body(mock_request)
        assert result["valid"] is False
        assert "Invalid JSON" in result["error"]

    @pytest.mark.asyncio
    async def test_validate_request_body_empty(self, middleware):
        """Test request body validation for empty body."""
        mock_request = Mock(spec=Request)
        mock_request.body = AsyncMock(return_value=b"")

        result = await middleware._validate_request_body(mock_request)
        assert result["valid"] is True

    def test_validate_order_service_data_valid_order_creation(self, middleware):
        """Test order service data validation for valid order creation."""
        data = {"items": [{"product_id": "123", "quantity": 2}], "total_amount": 100.0}

        result = middleware._validate_order_service_data(data, "/api/v1/orders")
        assert result["valid"] is True

    def test_validate_order_service_data_invalid_order_creation_missing_fields(
        self, middleware
    ):
        """Test order service data validation for invalid order creation."""
        data = {"items": []}  # Missing total_amount

        result = middleware._validate_order_service_data(data, "/api/v1/orders")
        assert result["valid"] is False
        assert "Missing required field" in result["error"]

    def test_validate_order_service_data_invalid_order_creation_empty_items(
        self, middleware
    ):
        """Test order service data validation for order creation with empty items."""
        data = {"items": [], "total_amount": 100.0}

        result = middleware._validate_order_service_data(data, "/api/v1/orders")
        assert result["valid"] is False
        assert "must be a non-empty array" in result["error"]

    def test_validate_order_service_data_invalid_order_creation_bad_quantity(
        self, middleware
    ):
        """Test order service data validation for order creation with invalid quantity."""
        data = {"items": [{"product_id": "123", "quantity": 0}], "total_amount": 100.0}

        result = middleware._validate_order_service_data(data, "/api/v1/orders")
        assert result["valid"] is False
        assert "must be a positive integer" in result["error"]

    def test_validate_order_service_data_invalid_order_creation_bad_amount(
        self, middleware
    ):
        """Test order service data validation for order creation with invalid amount."""
        data = {"items": [{"product_id": "123", "quantity": 1}], "total_amount": -10.0}

        result = middleware._validate_order_service_data(data, "/api/v1/orders")
        assert result["valid"] is False
        assert "must be a positive number" in result["error"]

    def test_validate_order_service_data_valid_order_update(self, middleware):
        """Test order service data validation for valid order update."""
        data = {"status": "shipped"}

        result = middleware._validate_order_service_data(data, "/api/v1/orders/123")
        assert result["valid"] is True

    def test_validate_order_service_data_invalid_order_update_dangerous_field(
        self, middleware
    ):
        """Test order service data validation for order update with dangerous fields."""
        data = {"id": "new_id", "total_amount": 200.0}

        result = middleware._validate_order_service_data(data, "/api/v1/orders/123")
        assert result["valid"] is False
        assert "cannot be updated directly" in result["error"]

    def test_validate_order_service_data_invalid_order_update_bad_status(
        self, middleware
    ):
        """Test order service data validation for order update with invalid status."""
        data = {"status": "invalid_status"}

        result = middleware._validate_order_service_data(data, "/api/v1/orders/123")
        assert result["valid"] is False
        assert "Invalid status" in result["error"]

    def test_validate_order_service_data_valid_payment(self, middleware):
        """Test order service data validation for valid payment."""
        data = {"order_id": "123", "amount": 100.0, "payment_method": "credit_card"}

        result = middleware._validate_order_service_data(data, "/api/v1/payments/456")
        assert result["valid"] is True

    def test_validate_order_service_data_invalid_payment_missing_fields(
        self, middleware
    ):
        """Test order service data validation for invalid payment."""
        data = {"amount": 100.0}  # Missing required fields

        result = middleware._validate_order_service_data(data, "/api/v1/payments/456")
        assert result["valid"] is False
        assert "Missing required field" in result["error"]

    def test_validate_order_service_data_invalid_payment_bad_method(self, middleware):
        """Test order service data validation for payment with invalid method."""
        data = {"order_id": "123", "amount": 100.0, "payment_method": "invalid_method"}

        result = middleware._validate_order_service_data(data, "/api/v1/payments/456")
        assert result["valid"] is False
        assert "Invalid payment method" in result["error"]

    def test_validate_order_service_data_valid_shipping(self, middleware):
        """Test order service data validation for valid shipping."""
        data = {
            "order_id": "123",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "country": "USA",
                "postal_code": "12345",
            },
            "carrier": "UPS",
        }

        result = middleware._validate_order_service_data(data, "/api/v1/shipping/456")
        assert result["valid"] is True

    def test_validate_order_service_data_invalid_shipping_missing_fields(
        self, middleware
    ):
        """Test order service data validation for invalid shipping."""
        data = {"carrier": "UPS"}  # Missing required fields

        result = middleware._validate_order_service_data(data, "/api/v1/shipping/456")
        assert result["valid"] is False
        assert "Missing required field" in result["error"]

    def test_validate_order_service_data_invalid_shipping_bad_address(self, middleware):
        """Test order service data validation for shipping with invalid address."""
        data = {
            "order_id": "123",
            "address": {"street": "123 Main St"},  # Missing required address fields
            "carrier": "UPS",
        }

        result = middleware._validate_order_service_data(data, "/api/v1/shipping/456")
        assert result["valid"] is False
        assert "Missing required address field" in result["error"]

    def test_validate_json_security_valid(self, middleware):
        """Test JSON security validation for valid data."""
        data = {"name": "test", "items": [1, 2, 3]}

        result = middleware._validate_json_security(data)
        assert result["valid"] is True

    def test_validate_json_security_too_deep(self, middleware):
        """Test JSON security validation for deeply nested data."""
        # Create deeply nested object
        data = {}
        current = data
        for i in range(15):  # Exceeds max_depth of 10
            current["nested"] = {}
            current = current["nested"]

        result = middleware._validate_json_security(data)
        assert result["valid"] is False
        assert "too deeply nested" in result["error"]

    def test_validate_json_security_large_array(self, middleware):
        """Test JSON security validation for large arrays."""
        data = {"items": list(range(2000))}  # Exceeds max_array_size of 1000

        result = middleware._validate_json_security(data)
        assert result["valid"] is False
        assert "larger than" in result["error"]

    def test_validate_json_security_dangerous_keys(self, middleware):
        """Test JSON security validation for dangerous keys."""
        data = {"__proto__": "malicious", "name": "test"}

        result = middleware._validate_json_security(data)
        assert result["valid"] is False
        assert "dangerous keys" in result["error"]

    def test_get_json_depth_simple(self, middleware):
        """Test JSON depth calculation for simple objects."""
        assert middleware._get_json_depth({"a": 1}) == 1
        assert middleware._get_json_depth({"a": {"b": 1}}) == 2
        assert middleware._get_json_depth([1, 2, 3]) == 1

    def test_has_large_array(self, middleware):
        """Test large array detection."""
        assert middleware._has_large_array([1] * 500, 1000) is False
        assert middleware._has_large_array([1] * 1500, 1000) is True
        assert middleware._has_large_array({"items": [1] * 1500}, 1000) is True

    def test_has_dangerous_keys(self, middleware):
        """Test dangerous key detection."""
        assert middleware._has_dangerous_keys({"name": "test"}, ["__proto__"]) is False
        assert (
            middleware._has_dangerous_keys({"__proto__": "bad"}, ["__proto__"]) is True
        )
        assert (
            middleware._has_dangerous_keys(
                {"data": {"__proto__": "bad"}}, ["__proto__"]
            )
            is True
        )

    @pytest.mark.asyncio
    async def test_dispatch_excluded_path(self, middleware):
        """Test that excluded paths bypass validation."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/health"
        mock_request.method = "GET"

        mock_call_next = AsyncMock(return_value=Mock())

        response = await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_dispatch_valid_request(self, middleware):
        """Test successful validation flow."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.state.correlation_id = "test-id"

        mock_response = Mock()
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response == mock_response
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_dispatch_size_validation_failure(self, middleware):
        """Test dispatch with size validation failure."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "POST"
        mock_request.headers = {"content-length": str(middleware.max_request_size + 1)}
        mock_request.state.correlation_id = "test-id"

        mock_call_next = AsyncMock()

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 413

        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_dispatch_content_type_validation_failure(self, middleware):
        """Test dispatch with content type validation failure."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "POST"
        mock_request.headers = {"content-type": "text/html"}
        mock_request.state.correlation_id = "test-id"

        mock_call_next = AsyncMock()

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 415

        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_dispatch_blocked_path(self, middleware):
        """Test dispatch with blocked path."""
        middleware.blocked_paths = ["/admin"]
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/admin/debug"
        mock_request.method = "GET"
        mock_request.headers = {}  # No content-length to avoid size validation
        mock_request.state.correlation_id = "test-id"

        mock_call_next = AsyncMock()

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 403

        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_dispatch_validation_exception(self, middleware):
        """Test dispatch with unexpected validation exception."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "POST"
        mock_request.headers = {}
        mock_request.state.correlation_id = "test-id"

        # Make _validate_request_size raise an exception
        middleware._validate_request_size = AsyncMock(
            side_effect=Exception("Test error")
        )

        mock_call_next = AsyncMock()

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 400

        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "validation_error"

    def test_setup_order_request_validation_middleware(self):
        """Test middleware setup function."""
        mock_app = Mock()

        setup_order_request_validation_middleware(mock_app)

        mock_app.add_middleware.assert_called_once()
        call_args = mock_app.add_middleware.call_args
        assert call_args[0][0] == OrderServiceRequestValidationMiddleware
