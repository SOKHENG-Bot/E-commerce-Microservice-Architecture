"""
Unit tests for Order Service Role Authorization Middleware.
"""

import json
from unittest.mock import AsyncMock, Mock

import pytest
from starlette.responses import JSONResponse

from order_service.app.middleware.auth.role_middleware import (
    OrderServiceRoleAuthorizationMiddleware,
    setup_order_role_authorization_middleware,
)


class TestOrderServiceRoleAuthorizationMiddleware:
    """Test cases for role authorization middleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance with default role requirements."""
        role_requirements = {
            "/api/v1/orders/admin": "admin",  # Admin-only order operations
            "/api/v1/orders/bulk": [
                "admin",
                "manager",
            ],  # Bulk operations require elevated access
            "/api/v1/orders/analytics": [
                "admin",
                "manager",
            ],  # Analytics require elevated access
            "/order-service": "admin",  # Management routes require admin
            "/api/v1/payments/admin": "admin",  # Payment admin operations
            "/api/v1/shipping/admin": "admin",  # Shipping admin operations
        }
        return OrderServiceRoleAuthorizationMiddleware(
            app=Mock(), role_requirements=role_requirements
        )

    @pytest.fixture
    def middleware_with_custom_roles(self):
        """Create middleware instance with custom role requirements."""
        role_requirements = {
            "/api/v1/orders/admin": "admin",
            "/api/v1/orders/manager": "manager",
            "/api/v1/orders/user": "user",
        }
        return OrderServiceRoleAuthorizationMiddleware(
            app=Mock(), role_requirements=role_requirements
        )

    def test_middleware_initialization(self, middleware):
        """Test middleware initializes correctly."""
        assert middleware.app is not None
        assert hasattr(middleware, "dispatch")
        assert middleware.role_requirements is not None
        assert middleware.exclude_paths is not None

    @pytest.mark.asyncio
    async def test_dispatch_admin_path_allowed_for_admin(self, middleware):
        """Test admin paths allow admin users."""
        mock_request = Mock()
        mock_request.url.path = "/api/v1/orders/admin/stats"
        mock_request.method = "GET"
        mock_request.state.user_role = "admin"
        mock_request.state.user_id = "123"
        mock_request.state.correlation_id = "test-correlation-id"

        mock_response = Mock()
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once_with(mock_request)
        assert response == mock_response

    @pytest.mark.asyncio
    async def test_dispatch_admin_path_denied_for_user(self, middleware):
        """Test admin paths deny regular users."""
        # Debug: check what role requirements the middleware has
        print(f"DEBUG: middleware.role_requirements = {middleware.role_requirements}")
        assert "/api/v1/orders/admin" in middleware.role_requirements
        print(
            f"DEBUG: path /api/v1/orders/admin/stats should match /api/v1/orders/admin: {'/api/v1/orders/admin/stats'.startswith('/api/v1/orders/admin')}"
        )

        mock_request = Mock()
        mock_request.url.path = "/api/v1/orders/admin/stats"
        mock_request.method = "GET"
        mock_request.state.user_role = "user"
        mock_request.state.user_id = "123"
        mock_request.state.correlation_id = "test-correlation-id"

        mock_call_next = AsyncMock()

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 403

        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "authorization_error"
        assert "Insufficient permissions" in response_data["error"]["message"]
        assert response_data["error"]["details"]["reason"] == "insufficient_role"

    @pytest.mark.asyncio
    async def test_dispatch_manager_path_allowed_for_manager(self, middleware):
        """Test manager paths allow manager users."""
        mock_request = Mock()
        mock_request.url.path = "/api/v1/orders/bulk/operations"
        mock_request.method = "POST"
        mock_request.state.user_role = "manager"
        mock_request.state.user_id = "123"
        mock_request.state.correlation_id = "test-correlation-id"

        mock_response = Mock()
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once_with(mock_request)
        assert response == mock_response

    @pytest.mark.asyncio
    async def test_dispatch_manager_path_allowed_for_admin(self, middleware):
        """Test manager paths allow admin users."""
        mock_request = Mock()
        mock_request.url.path = "/api/v1/orders/bulk/operations"
        mock_request.method = "POST"
        mock_request.state.user_role = "admin"
        mock_request.state.user_id = "123"
        mock_request.state.correlation_id = "test-correlation-id"

        mock_response = Mock()
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once_with(mock_request)
        assert response == mock_response

    @pytest.mark.asyncio
    async def test_dispatch_manager_path_denied_for_user(self, middleware):
        """Test manager paths deny regular users."""
        mock_request = Mock()
        mock_request.url.path = "/api/v1/orders/bulk/operations"
        mock_request.method = "POST"
        mock_request.state.user_role = "user"
        mock_request.state.user_id = "123"
        mock_request.state.correlation_id = "test-correlation-id"

        mock_call_next = AsyncMock()

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 403

        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "authorization_error"
        assert "Insufficient permissions" in response_data["error"]["message"]

    @pytest.mark.asyncio
    async def test_dispatch_regular_path_allowed_for_all(self, middleware):
        """Test regular paths allow all authenticated users."""
        for role in ["user", "manager", "admin"]:
            mock_request = Mock()
            mock_request.url.path = "/api/v1/orders"
            mock_request.method = "GET"
            mock_request.state.user_role = role
            mock_request.state.user_id = "123"
            mock_request.state.correlation_id = "test-correlation-id"

            mock_response = Mock()
            mock_call_next = AsyncMock(return_value=mock_response)

            response = await middleware.dispatch(mock_request, mock_call_next)

            mock_call_next.assert_called_once_with(mock_request)
            assert response == mock_response

    @pytest.mark.asyncio
    async def test_dispatch_no_user_role(self, middleware):
        """Test request without user role defaults to user."""
        mock_request = Mock()
        mock_request.url.path = "/api/v1/orders/admin/stats"
        mock_request.method = "GET"
        mock_request.state.user_id = "123"
        mock_request.state.correlation_id = "test-correlation-id"
        # No user_role set - should default to "user"
        del mock_request.state.user_role  # Ensure no user_role attribute

        mock_call_next = AsyncMock()

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should deny access because default "user" role doesn't have admin access
        assert isinstance(response, JSONResponse)
        assert response.status_code == 403

        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "authorization_error"

    @pytest.mark.asyncio
    async def test_dispatch_no_user_id(self, middleware):
        """Test request without user ID."""
        mock_request = Mock()
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "GET"
        mock_request.state.user_role = "user"
        mock_request.state.correlation_id = "test-correlation-id"
        # No user_id set

        mock_response = Mock()
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should still proceed since it's not a protected path
        mock_call_next.assert_called_once_with(mock_request)
        assert response == mock_response

    @pytest.mark.asyncio
    async def test_dispatch_exception_handling(self, middleware):
        """Test exception handling in middleware."""
        mock_request = Mock()
        mock_request.url.path = "/api/v1/orders"
        mock_request.method = "GET"
        mock_request.state.user_role = "user"
        mock_request.state.user_id = "123"
        mock_request.state.correlation_id = "test-correlation-id"

        # Make call_next raise an exception
        mock_call_next = AsyncMock(side_effect=Exception("Internal error"))

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should return 500 error response
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

        response_data = json.loads(response.body)
        assert response_data["error"]["type"] == "authorization_system_error"
        assert "Authorization system error" in response_data["error"]["message"]

    @pytest.mark.asyncio
    async def test_dispatch_exclude_paths(self, middleware):
        """Test excluded paths skip authorization."""
        for path in ["/health", "/docs", "/api/v1/orders/health"]:
            mock_request = Mock()
            mock_request.url.path = path
            mock_request.method = "GET"

            mock_response = Mock()
            mock_call_next = AsyncMock(return_value=mock_response)

            response = await middleware.dispatch(mock_request, mock_call_next)

            mock_call_next.assert_called_once_with(mock_request)
            assert response == mock_response

    def test_should_skip_auth(self, middleware):
        """Test auth skipping logic."""
        # Should skip
        assert middleware._should_skip_auth("/health") is True
        assert middleware._should_skip_auth("/docs") is True
        assert middleware._should_skip_auth("/api/v1/orders/health") is True
        assert middleware._should_skip_auth("/api/v1/orders/health/check") is True

        # Should not skip
        assert middleware._should_skip_auth("/api/v1/orders") is False
        assert middleware._should_skip_auth("/api/v1/orders/admin") is False

    def test_check_role_authorization_no_requirements(self, middleware):
        """Test role checking when no requirements exist."""
        result = middleware._check_role_authorization(
            "/api/v1/orders/regular", "GET", "user", []
        )
        assert result["authorized"] is True
        assert result["reason"] == "no_role_requirements"

    def test_check_role_authorization_with_requirements(self, middleware):
        """Test role checking with requirements."""
        # Test admin requirement
        result = middleware._check_role_authorization(
            "/api/v1/orders/admin/stats", "GET", "admin", []
        )
        assert result["authorized"] is True

        result = middleware._check_role_authorization(
            "/api/v1/orders/admin/stats", "GET", "user", []
        )
        assert result["authorized"] is False
        assert result["reason"] == "insufficient_role"

        # Test manager requirement
        result = middleware._check_role_authorization(
            "/api/v1/orders/bulk", "POST", "manager", []
        )
        assert result["authorized"] is True

        result = middleware._check_role_authorization(
            "/api/v1/orders/bulk", "POST", "user", []
        )
        assert result["authorized"] is False

    def test_validate_roles_single_role(self, middleware):
        """Test role validation with single required role."""
        # User has required role
        result = middleware._validate_roles("admin", "admin", [])
        assert result["authorized"] is True
        assert result["matched_role"] == "admin"

        # User doesn't have required role
        result = middleware._validate_roles("admin", "user", [])
        assert result["authorized"] is False
        assert result["reason"] == "insufficient_role"

    def test_validate_roles_multiple_roles(self, middleware):
        """Test role validation with multiple required roles."""
        # User has one of the required roles
        result = middleware._validate_roles(["admin", "manager"], "admin", [])
        assert result["authorized"] is True
        assert result["matched_role"] == "admin"

        # User doesn't have any required roles
        result = middleware._validate_roles(["admin", "manager"], "user", [])
        assert result["authorized"] is False
        assert result["reason"] == "insufficient_role"

    def test_validate_roles_with_user_roles_list(self, middleware):
        """Test role validation using user_roles list."""
        # Role found in user_roles list
        result = middleware._validate_roles("manager", "user", ["manager", "editor"])
        assert result["authorized"] is True
        assert result["matched_role"] == "manager"

        # Role not found
        result = middleware._validate_roles("admin", "user", ["manager", "editor"])
        assert result["authorized"] is False

    def test_check_role_authorization_direct(self, middleware):
        """Test role authorization checking directly."""
        # Debug: check what role requirements the middleware has
        print(f"DEBUG: middleware.role_requirements = {middleware.role_requirements}")

        # Test admin path
        result = middleware._check_role_authorization(
            "/api/v1/orders/admin/stats", "GET", "user", []
        )
        print(f"DEBUG: result for admin path = {result}")
        assert result["authorized"] is False
        assert result["reason"] == "insufficient_role"

    def test_setup_order_role_authorization_middleware(self):
        """Test middleware setup function."""
        mock_app = Mock()

        setup_order_role_authorization_middleware(mock_app)

        mock_app.add_middleware.assert_called_once()
        call_args = mock_app.add_middleware.call_args
        assert call_args[0][0] == OrderServiceRoleAuthorizationMiddleware
