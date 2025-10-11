"""
Unit tests for Order Service Error Handler.
"""

import json
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from order_service.app.middleware.error.error_handler import (
    OrderServiceErrorHandler,
    setup_order_error_handling,
)


class TestOrderServiceErrorHandler:
    """Test cases for error handler."""

    @pytest.fixture
    def app(self):
        """Create FastAPI app for testing."""
        return FastAPI()

    @pytest.fixture
    def error_handler(self):
        """Create error handler instance."""
        return OrderServiceErrorHandler()

    def test_setup_error_handlers(self, app):
        """Test that error handlers are properly set up."""
        OrderServiceErrorHandler.setup_error_handlers(app)

        # Check that exception handlers are registered
        assert len(app.exception_handlers) > 0
        assert StarletteHTTPException in app.exception_handlers
        assert RequestValidationError in app.exception_handlers
        assert ValidationError in app.exception_handlers
        assert ValueError in app.exception_handlers
        assert PermissionError in app.exception_handlers
        assert Exception in app.exception_handlers

    @pytest.mark.asyncio
    async def test_http_exception_handler(self, app):
        """Test HTTP exception handling."""
        OrderServiceErrorHandler.setup_error_handlers(app)

        # Create a mock request
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "GET"
        mock_request.state.correlation_id = "test-correlation-id"
        mock_request.state.user_id = "123"

        # Create HTTP exception
        exc = StarletteHTTPException(status_code=404, detail="Not found")

        # Get the handler
        handler = app.exception_handlers[StarletteHTTPException]

        # Call the handler
        response = await handler(mock_request, exc)

        assert response.status_code == 404
        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "http_error"
        assert response_data["error"]["message"] == "Not found"
        assert response_data["error"]["correlation_id"] == "test-correlation-id"
        assert response_data["error"]["user_id"] == "123"

    @pytest.mark.asyncio
    async def test_request_validation_error_handler(self, app):
        """Test request validation error handling."""
        OrderServiceErrorHandler.setup_error_handlers(app)

        # Create a mock request
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "POST"
        mock_request.state.correlation_id = "test-correlation-id"
        mock_request.state.user_id = "123"

        # Create validation error
        exc = RequestValidationError(
            [
                {
                    "loc": ["body", "items"],
                    "msg": "field required",
                    "type": "value_error.missing",
                }
            ]
        )

        # Get the handler
        handler = app.exception_handlers[RequestValidationError]

        # Call the handler
        response = await handler(mock_request, exc)

        assert response.status_code == 422
        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "validation_error"
        assert "Request validation failed" in response_data["error"]["message"]
        assert len(response_data["error"]["details"]["validation_errors"]) == 1

    @pytest.mark.asyncio
    async def test_value_error_handler(self, app):
        """Test ValueError handling."""
        OrderServiceErrorHandler.setup_error_handlers(app)

        # Create a mock request
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "POST"
        mock_request.state.correlation_id = "test-correlation-id"
        mock_request.state.user_id = "123"

        # Create ValueError
        exc = ValueError("Invalid input")

        # Get the handler
        handler = app.exception_handlers[ValueError]

        # Call the handler
        response = await handler(mock_request, exc)

        assert response.status_code == 400
        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "value_error"
        assert response_data["error"]["message"] == "Invalid input"

    @pytest.mark.asyncio
    async def test_permission_error_handler(self, app):
        """Test PermissionError handling."""
        OrderServiceErrorHandler.setup_error_handlers(app)

        # Create a mock request
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "POST"
        mock_request.state.correlation_id = "test-correlation-id"
        mock_request.state.user_id = "123"

        # Create PermissionError
        exc = PermissionError("Access denied")

        # Get the handler
        handler = app.exception_handlers[PermissionError]

        # Call the handler
        response = await handler(mock_request, exc)

        assert response.status_code == 403
        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "permission_error"
        assert response_data["error"]["message"] == "Insufficient permissions"

    @pytest.mark.asyncio
    async def test_order_business_exception_handler_order_error(self, app):
        """Test order-specific business exception handling."""
        OrderServiceErrorHandler.setup_error_handlers(app)

        # Create a mock request
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "POST"
        mock_request.state.correlation_id = "test-correlation-id"
        mock_request.state.user_id = "123"

        # Create order-related exception
        exc = Exception("Order not found")

        # Get the handler (the general Exception handler handles order-specific logic)
        handler = app.exception_handlers[Exception]

        # Call the handler
        response = await handler(mock_request, exc)

        assert response.status_code == 400
        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "order_error"
        assert response_data["error"]["message"] == "Order not found"
        assert response_data["error"]["details"]["domain"] == "order"

    @pytest.mark.asyncio
    async def test_order_business_exception_handler_payment_error(self, app):
        """Test payment-specific business exception handling."""
        OrderServiceErrorHandler.setup_error_handlers(app)

        # Create a mock request
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/payments"
        mock_request.method = "POST"
        mock_request.state.correlation_id = "test-correlation-id"
        mock_request.state.user_id = "123"

        # Create payment-related exception
        exc = Exception("Payment processing failed")

        # Get the handler
        handler = app.exception_handlers[Exception]

        # Call the handler
        response = await handler(mock_request, exc)

        assert response.status_code == 400
        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "payment_error"
        assert response_data["error"]["message"] == "Payment processing failed"
        assert response_data["error"]["details"]["domain"] == "payment"

    @pytest.mark.asyncio
    async def test_order_business_exception_handler_shipping_error(self, app):
        """Test shipping-specific business exception handling."""
        OrderServiceErrorHandler.setup_error_handlers(app)

        # Create a mock request
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/shipping"
        mock_request.method = "POST"
        mock_request.state.correlation_id = "test-correlation-id"
        mock_request.state.user_id = "123"

        # Create shipping-related exception
        exc = Exception("Shipping address invalid")

        # Get the handler
        handler = app.exception_handlers[Exception]

        # Call the handler
        response = await handler(mock_request, exc)

        assert response.status_code == 400
        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "shipping_error"
        assert response_data["error"]["message"] == "Shipping address invalid"
        assert response_data["error"]["details"]["domain"] == "shipping"

    @pytest.mark.asyncio
    async def test_order_business_exception_handler_inventory_error(self, app):
        """Test inventory-specific business exception handling."""
        OrderServiceErrorHandler.setup_error_handlers(app)

        # Create a mock request
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "POST"
        mock_request.state.correlation_id = "test-correlation-id"
        mock_request.state.user_id = "123"

        # Create inventory-related exception
        exc = Exception("Out of stock")

        # Get the handler
        handler = app.exception_handlers[Exception]

        # Call the handler
        response = await handler(mock_request, exc)

        assert response.status_code == 409
        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "inventory_error"
        assert response_data["error"]["message"] == "Out of stock"
        assert response_data["error"]["details"]["domain"] == "inventory"

    @pytest.mark.asyncio
    async def test_general_exception_handler(self, app):
        """Test general exception handling."""
        OrderServiceErrorHandler.setup_error_handlers(app)

        # Create a mock request
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "POST"
        mock_request.state.correlation_id = "test-correlation-id"
        mock_request.state.user_id = "123"

        # Create general exception
        exc = Exception("Unexpected error")

        # Get the handler
        handler = app.exception_handlers[Exception]

        # Call the handler
        response = await handler(mock_request, exc)

        assert response.status_code == 500
        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "internal_server_error"
        assert "An internal server error occurred" in response_data["error"]["message"]

    def test_create_error_response_basic(self):
        """Test basic error response creation."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "GET"
        mock_request.state.correlation_id = "test-correlation-id"
        mock_request.state.user_id = "123"

        response = OrderServiceErrorHandler._create_error_response(
            request=mock_request,
            status_code=400,
            error_type="test_error",
            message="Test message",
        )

        assert response.status_code == 400
        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "test_error"
        assert response_data["error"]["message"] == "Test message"
        assert response_data["error"]["correlation_id"] == "test-correlation-id"
        assert response_data["error"]["user_id"] == "123"
        assert "timestamp" in response_data["error"]

    def test_create_error_response_with_details(self):
        """Test error response creation with details."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "GET"
        mock_request.state.correlation_id = "test-correlation-id"
        mock_request.state.user_id = "123"

        details = {"field": "name", "reason": "required"}

        response = OrderServiceErrorHandler._create_error_response(
            request=mock_request,
            status_code=422,
            error_type="validation_error",
            message="Validation failed",
            details=details,
        )

        assert response.status_code == 422
        response_data = json.loads(response.body)
        assert response_data["error"]["details"] == details

    def test_create_error_response_missing_correlation_id(self):
        """Test error response when correlation_id is missing."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "GET"
        # No correlation_id set
        del mock_request.state.correlation_id
        mock_request.state.user_id = "123"

        response = OrderServiceErrorHandler._create_error_response(
            request=mock_request,
            status_code=500,
            error_type="server_error",
            message="Server error",
        )

        response_data = json.loads(response.body)
        assert response_data["error"]["correlation_id"] == "unknown"
        assert response_data["error"]["user_id"] == "123"

    def test_create_error_response_missing_user_id(self):
        """Test error response when user_id is missing."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "GET"
        mock_request.state.correlation_id = "test-correlation-id"
        # No user_id set
        del mock_request.state.user_id

        response = OrderServiceErrorHandler._create_error_response(
            request=mock_request,
            status_code=500,
            error_type="server_error",
            message="Server error",
        )

        response_data = json.loads(response.body)
        assert response_data["error"]["correlation_id"] == "test-correlation-id"
        assert response_data["error"]["user_id"] == "anonymous"

    def test_setup_order_error_handling(self, app):
        """Test the convenience setup function."""
        setup_order_error_handling(app)

        # Check that exception handlers are registered
        assert len(app.exception_handlers) > 0
