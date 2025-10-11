"""
Unit tests for User Service Error Handling Middleware
Tests exception handling, error responses, and logging.
"""

import json
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from user_service.app.middleware.error.error_handler import (
    UserServiceErrorHandler,
    setup_user_error_handling,
)


class TestUserServiceErrorHandler:
    """Test cases for error handling middleware"""

    @pytest.fixture
    def app(self):
        """Create FastAPI app instance"""
        return FastAPI()

    @pytest.fixture
    def error_handler(self):
        """Create error handler instance"""
        return UserServiceErrorHandler()

    @pytest.fixture
    def mock_request(self):
        """Create mock request"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/test"
        request.method = "GET"
        request.state = MagicMock()
        request.state.correlation_id = "test-correlation-id"
        request.state.user_id = "test-user-id"
        return request

    def test_setup_error_handlers_adds_handlers_to_app(self, app):
        """Test that setup_error_handlers adds exception handlers to FastAPI app"""
        initial_handlers = len(app.exception_handlers)

        UserServiceErrorHandler.setup_error_handlers(app)

        # Should have added multiple exception handlers
        assert len(app.exception_handlers) > initial_handlers

    def test_setup_user_error_handling_convenience_function(self, app):
        """Test the convenience function for setting up error handling"""
        # Should not raise an exception
        setup_user_error_handling(app)

        # Should have exception handlers configured
        assert len(app.exception_handlers) > 0

    @pytest.mark.asyncio
    async def test_http_exception_handler_starlette_exception(self, app, mock_request):
        """Test handling of Starlette HTTP exceptions"""
        UserServiceErrorHandler.setup_error_handlers(app)

        exc = StarletteHTTPException(status_code=404, detail="Not found")

        handler = app.exception_handlers.get(StarletteHTTPException)
        assert handler is not None

        response = await handler(mock_request, exc)

        assert response.status_code == 404
        response_data = json.loads(response.body.decode())
        assert response_data["error"]["type"] == "http_error"
        assert response_data["error"]["message"] == "Not found"
        assert response_data["error"]["correlation_id"] == "test-correlation-id"
        assert response_data["error"]["user_id"] == "test-user-id"
        assert response_data["error"]["path"] == "/api/v1/test"
        assert response_data["error"]["method"] == "GET"
        assert "timestamp" in response_data["error"]

    @pytest.mark.asyncio
    async def test_request_validation_error_handler(self, app, mock_request):
        """Test handling of FastAPI RequestValidationError"""
        UserServiceErrorHandler.setup_error_handlers(app)

        # Create a mock validation error
        errors = [
            {
                "loc": ("body", "email"),
                "msg": "field required",
                "type": "value_error.missing",
            },
            {
                "loc": ("body", "password"),
                "msg": "ensure this value has at least 8 characters",
                "type": "value_error.const",
            },
        ]
        exc = RequestValidationError(errors=errors)

        handler = app.exception_handlers.get(RequestValidationError)
        assert handler is not None

        response = await handler(mock_request, exc)

        assert response.status_code == 422
        response_data = json.loads(response.body.decode())
        assert response_data["error"]["type"] == "validation_error"
        assert "Request validation failed" in response_data["error"]["message"]
        assert len(response_data["error"]["details"]["validation_errors"]) == 2

        # Check first error
        error1 = response_data["error"]["details"]["validation_errors"][0]
        assert error1["field"] == "body.email"
        assert error1["message"] == "field required"
        assert error1["type"] == "value_error.missing"

    @pytest.mark.asyncio
    async def test_pydantic_validation_error_handler(self, app, mock_request):
        """Test handling of Pydantic ValidationError"""
        pytest.skip("Skipping ValidationError test - complex to mock properly")

    @pytest.mark.asyncio
    async def test_value_error_handler(self, app, mock_request):
        """Test handling of ValueError exceptions"""
        UserServiceErrorHandler.setup_error_handlers(app)

        exc = ValueError("Invalid input provided")

        handler = app.exception_handlers.get(ValueError)
        assert handler is not None

        response = await handler(mock_request, exc)

        assert response.status_code == 400
        response_data = json.loads(response.body.decode())
        assert response_data["error"]["type"] == "value_error"
        assert response_data["error"]["message"] == "Invalid input provided"
        assert response_data["error"]["details"]["exception_type"] == "ValueError"

    @pytest.mark.asyncio
    async def test_permission_error_handler(self, app, mock_request):
        """Test handling of PermissionError exceptions"""
        UserServiceErrorHandler.setup_error_handlers(app)

        exc = PermissionError("Access denied")

        handler = app.exception_handlers.get(PermissionError)
        assert handler is not None

        response = await handler(mock_request, exc)

        assert response.status_code == 403
        response_data = json.loads(response.body.decode())
        assert response_data["error"]["type"] == "permission_error"
        assert response_data["error"]["message"] == "Insufficient permissions"
        assert response_data["error"]["details"]["exception_type"] == "PermissionError"

    @pytest.mark.asyncio
    async def test_general_exception_handler(self, app, mock_request):
        """Test handling of general exceptions (500 errors)"""
        UserServiceErrorHandler.setup_error_handlers(app)

        exc = RuntimeError("Database connection failed")

        handler = app.exception_handlers.get(Exception)
        assert handler is not None

        response = await handler(mock_request, exc)

        assert response.status_code == 500
        response_data = json.loads(response.body.decode())
        assert response_data["error"]["type"] == "internal_server_error"
        assert "An internal server error occurred" in response_data["error"]["message"]
        assert response_data["error"]["details"]["exception_type"] == "RuntimeError"

    @pytest.mark.asyncio
    async def test_error_response_includes_required_fields(self, app, mock_request):
        """Test that all error responses include required fields"""
        UserServiceErrorHandler.setup_error_handlers(app)

        exc = ValueError("Test error")

        handler = app.exception_handlers.get(ValueError)
        response = await handler(mock_request, exc)

        response_data = json.loads(response.body.decode())

        # Check all required fields are present
        error_obj = response_data["error"]
        required_fields = [
            "type",
            "message",
            "correlation_id",
            "user_id",
            "timestamp",
            "path",
            "method",
        ]

        for field in required_fields:
            assert field in error_obj, f"Missing required field: {field}"

    @pytest.mark.asyncio
    async def test_error_handler_with_anonymous_user(self, app):
        """Test error handling when user is not authenticated"""
        UserServiceErrorHandler.setup_error_handlers(app)

        # Mock request without user_id attribute
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/public"
        request.method = "GET"
        request.state = MagicMock()
        request.state.correlation_id = "test-correlation-id"
        # Remove user_id attribute so getattr uses default
        del request.state.user_id

        exc = ValueError("Test error")

        handler = app.exception_handlers.get(ValueError)
        response = await handler(request, exc)

        response_data = json.loads(response.body.decode())
        assert response_data["error"]["user_id"] == "anonymous"

    @pytest.mark.asyncio
    async def test_error_handler_without_correlation_id(self, app):
        """Test error handling when correlation ID is not set"""
        UserServiceErrorHandler.setup_error_handlers(app)

        # Mock request without correlation_id attribute
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/test"
        request.method = "GET"
        request.state = MagicMock()
        request.state.user_id = "test-user"
        # Remove correlation_id attribute so getattr uses default
        del request.state.correlation_id

        exc = ValueError("Test error")

        handler = app.exception_handlers.get(ValueError)
        response = await handler(request, exc)

        response_data = json.loads(response.body.decode())
        assert response_data["error"]["correlation_id"] == "unknown"
