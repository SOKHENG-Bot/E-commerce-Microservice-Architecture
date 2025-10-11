"""
Unit tests for Order Service Authentication Middleware.
"""

import json
from unittest.mock import AsyncMock, Mock

import pytest
from starlette.responses import JSONResponse

from order_service.app.middleware.auth.auth_middleware import (
    OrderServiceAuthMiddleware,
    setup_order_auth_middleware,
)


class TestOrderServiceAuthMiddleware:
    """Test cases for authentication middleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance for testing."""
        return OrderServiceAuthMiddleware(app=Mock())

    @pytest.fixture
    def jwt_handler_mock(self):
        """Mock JWT handler."""
        from unittest.mock import MagicMock

        # Create a mock TokenData object
        mock_token_data = MagicMock()
        mock_token_data.user_id = "123"
        mock_token_data.email = "test@example.com"
        mock_token_data.username = "testuser"
        mock_token_data.roles = ["user"]
        mock_token_data.permissions = []
        mock_token_data.expires_at = MagicMock()
        mock_token_data.expires_at.timestamp.return_value = 9999999999

        mock_handler = Mock()
        mock_handler.decode_token.return_value = mock_token_data
        return mock_handler

    def test_exclude_paths_default(self, middleware):
        """Test default exclude paths."""
        assert "/health" in middleware.exclude_paths
        assert "/docs" in middleware.exclude_paths
        assert "/api/v1/orders/health" in middleware.exclude_paths

    def test_should_skip_auth_excluded_path(self, middleware):
        """Test that excluded paths skip authentication."""
        mock_request = Mock()
        mock_request.url.path = "/health"
        assert middleware._should_skip_auth("/health") is True

        mock_request.url.path = "/api/v1/orders/health"
        assert middleware._should_skip_auth("/api/v1/orders/health") is True

    def test_should_skip_auth_normal_path(self, middleware):
        """Test that normal paths don't skip authentication."""
        assert middleware._should_skip_auth("/api/v1/orders") is False
        assert middleware._should_skip_auth("/api/v1/orders/123") is False

    def test_should_skip_auth_prefix_match(self, middleware):
        """Test prefix matching for excluded paths."""
        middleware.exclude_paths = ["/docs"]
        assert middleware._should_skip_auth("/docs") is True
        assert middleware._should_skip_auth("/docs/") is True
        assert middleware._should_skip_auth("/docs/redoc") is True

    @pytest.mark.asyncio
    async def test_authenticate_request_no_token(self, middleware):
        """Test authentication with no token."""
        mock_request = Mock()
        mock_request.cookies = {}

        result = await middleware._authenticate_request(mock_request)

        assert result["authenticated"] is False
        assert result["reason"] == "missing_auth_cookie"

    @pytest.mark.asyncio
    async def test_authenticate_request_empty_token(self, middleware):
        """Test authentication with empty token."""
        mock_request = Mock()
        mock_request.cookies = {"auth_token": "   "}  # Whitespace-only token

        result = await middleware._authenticate_request(mock_request)

        assert result["authenticated"] is False
        assert result["reason"] == "empty_cookie_token"

    @pytest.mark.asyncio
    async def test_authenticate_request_null_token(self, middleware):
        """Test authentication with null token."""
        mock_request = Mock()
        mock_request.cookies = {"auth_token": "null"}

        result = await middleware._authenticate_request(mock_request)

        assert result["authenticated"] is False
        assert result["reason"] == "empty_cookie_token"

    @pytest.mark.asyncio
    async def test_authenticate_request_valid_token(self, middleware, jwt_handler_mock):
        """Test authentication with valid token."""
        middleware.jwt_handler = jwt_handler_mock

        mock_request = Mock()
        mock_request.cookies = {"auth_token": "valid.jwt.token"}

        result = await middleware._authenticate_request(mock_request)

        assert result["authenticated"] is True
        assert result["user_id"] == "123"
        assert result["user_role"] == "user"
        assert result["token_data"]["user_id"] == "123"
        assert result["token_source"] == "cookie"

    @pytest.mark.asyncio
    async def test_authenticate_request_invalid_token(
        self, middleware, jwt_handler_mock
    ):
        """Test authentication with invalid token."""
        jwt_handler_mock.decode_token.side_effect = ValueError("Invalid token")
        middleware.jwt_handler = jwt_handler_mock

        mock_request = Mock()
        mock_request.cookies = {"auth_token": "invalid.jwt.token"}

        result = await middleware._authenticate_request(mock_request)

        assert result["authenticated"] is False
        assert result["reason"] == "invalid_cookie_token"

    @pytest.mark.asyncio
    async def test_authenticate_request_access_token_fallback(
        self, middleware, jwt_handler_mock
    ):
        """Test authentication with access_token cookie fallback."""
        middleware.jwt_handler = jwt_handler_mock

        mock_request = Mock()
        mock_request.cookies = {"access_token": "valid.jwt.token"}

        result = await middleware._authenticate_request(mock_request)

        assert result["authenticated"] is True
        assert result["token_source"] == "cookie"

    @pytest.mark.asyncio
    async def test_dispatch_excluded_path(self, middleware):
        """Test that excluded paths bypass authentication."""
        mock_request = Mock()
        mock_request.url.path = "/health"
        mock_call_next = AsyncMock(return_value=Mock())

        response = await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once_with(mock_request)
        assert response is not None

    @pytest.mark.asyncio
    async def test_dispatch_successful_auth(self, middleware, jwt_handler_mock):
        """Test successful authentication flow."""
        middleware.jwt_handler = jwt_handler_mock

        mock_request = Mock()
        mock_request.url.path = "/api/v1/orders"
        mock_request.cookies = {"auth_token": "valid.jwt.token"}
        mock_request.state = Mock()
        mock_request.method = "GET"

        mock_response = Mock()
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response == mock_response
        assert mock_request.state.user_id == "123"
        assert mock_request.state.user_role == "user"
        assert mock_request.state.token_data is not None

    @pytest.mark.asyncio
    async def test_dispatch_failed_auth(self, middleware):
        """Test failed authentication returns 401."""
        mock_request = Mock()
        mock_request.url.path = "/api/v1/orders"
        mock_request.cookies = {}
        mock_request.method = "GET"
        mock_request.state.correlation_id = "test-correlation-id"  # Set as string

        mock_call_next = AsyncMock()
        middleware._authenticate_request = AsyncMock(
            return_value={"authenticated": False, "reason": "missing_auth_cookie"}
        )

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 401

        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "authentication_error"
        assert "Authentication required" in response_data["error"]["message"]

    @pytest.mark.asyncio
    async def test_dispatch_auth_exception(self, middleware):
        """Test that auth exceptions return 500."""
        mock_request = Mock()
        mock_request.url.path = "/api/v1/orders"
        mock_request.cookies = {"auth_token": "token"}
        mock_request.method = "GET"
        mock_request.state.correlation_id = "test-correlation-id"  # Set as string

        middleware._authenticate_request = AsyncMock(
            side_effect=Exception("Auth error")
        )

        response = await middleware.dispatch(mock_request, AsyncMock())

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "authentication_system_error"

    @pytest.mark.asyncio
    async def test_validate_token_no_handler(self, middleware):
        """Test token validation without JWT handler (fallback)."""
        middleware.jwt_handler = None

        result = await middleware._validate_token("short")

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_token_development_fallback(self, middleware):
        """Test development fallback for token validation."""
        middleware.jwt_handler = None

        result = await middleware._validate_token("long.enough.token.for.development")

        assert result is not None
        assert result["user_id"] == "dev_user_123"
        assert result["role"] == "user"

    def test_setup_order_auth_middleware(self):
        """Test middleware setup function."""
        mock_app = Mock()

        setup_order_auth_middleware(mock_app)

        mock_app.add_middleware.assert_called_once()
        call_args = mock_app.add_middleware.call_args
        assert call_args[0][0] == OrderServiceAuthMiddleware

    def test_setup_order_auth_middleware_custom_excludes(self):
        """Test middleware setup with custom exclude paths."""
        mock_app = Mock()
        custom_excludes = ["/custom", "/health"]

        setup_order_auth_middleware(mock_app, exclude_paths=custom_excludes)

        call_args = mock_app.add_middleware.call_args
        # The middleware class is the first positional argument
        assert call_args[0][0] == OrderServiceAuthMiddleware
        # The exclude_paths should be passed as a keyword argument
        assert call_args[1]["exclude_paths"] == custom_excludes

    def test_setup_order_auth_middleware_with_jwt_handler(self):
        """Test middleware setup with custom JWT handler."""
        mock_app = Mock()
        mock_jwt_handler = Mock()

        setup_order_auth_middleware(mock_app, jwt_handler=mock_jwt_handler)

        call_args = mock_app.add_middleware.call_args
        middleware_kwargs = call_args[1]
        assert middleware_kwargs["jwt_handler"] == mock_jwt_handler
