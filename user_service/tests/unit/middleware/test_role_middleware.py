"""
Unit tests for User Service Role Authorization Middleware
Tests role-based access control and authorization flow.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from user_service.app.middleware.auth.role_middleware import (
    UserServiceRoleAuthorizationMiddleware,
    setup_user_role_authorization_middleware,
)


class TestUserServiceRoleAuthorizationMiddleware:
    """Test cases for role authorization middleware"""

    @pytest.fixture
    def middleware(self):
        """Create role authorization middleware instance"""
        app = FastAPI()
        role_requirements = {
            "/api/v1/users": "admin",
            "/api/v1/permissions": ["admin", "moderator"],
            "/api/v1/admin": "admin",
        }
        return UserServiceRoleAuthorizationMiddleware(
            app=app,
            role_requirements=role_requirements,
            exclude_paths=["/health", "/docs"],
        )

    @pytest.fixture
    def mock_request(self):
        """Create mock request"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/users"
        request.method = "GET"
        request.headers = {}
        request.state = MagicMock()
        request.state.correlation_id = "test-correlation-id"
        return request

    def test_should_skip_auth_excluded_paths(self, middleware):
        """Test that excluded paths skip authorization"""
        excluded_paths = [
            "/health",
            "/docs",
        ]  # Only test paths that are actually excluded

        for path in excluded_paths:
            assert middleware._should_skip_auth(path)

        assert not middleware._should_skip_auth("/api/v1/users")

    def test_should_skip_auth_prefix_matches(self, middleware):
        """Test that path prefixes are properly excluded"""
        assert middleware._should_skip_auth("/docs/swagger")
        assert middleware._should_skip_auth("/docs/redoc")
        assert not middleware._should_skip_auth("/api/docs")

    def test_check_role_authorization_exact_match(self, middleware):
        """Test role authorization with exact path match"""
        # Test admin requirement
        result = middleware._check_role_authorization(
            "/api/v1/users", "GET", "admin", []
        )
        assert result["authorized"] is True
        assert result["required_roles"] == ["admin"]
        assert result["matched_role"] == "admin"

        # Test insufficient role
        result = middleware._check_role_authorization(
            "/api/v1/users", "GET", "user", []
        )
        assert result["authorized"] is False
        assert result["reason"] == "insufficient_role"
        assert result["required_roles"] == ["admin"]

    def test_check_role_authorization_multiple_roles(self, middleware):
        """Test role authorization with multiple required roles"""
        # Test with allowed role
        result = middleware._check_role_authorization(
            "/api/v1/permissions", "GET", "admin", []
        )
        assert result["authorized"] is True
        assert result["matched_role"] == "admin"

        result = middleware._check_role_authorization(
            "/api/v1/permissions", "GET", "moderator", []
        )
        assert result["authorized"] is True
        assert result["matched_role"] == "moderator"

        # Test with insufficient role
        result = middleware._check_role_authorization(
            "/api/v1/permissions", "GET", "user", []
        )
        assert result["authorized"] is False
        assert result["required_roles"] == ["admin", "moderator"]

    def test_check_role_authorization_no_requirements(self, middleware):
        """Test paths with no role requirements"""
        result = middleware._check_role_authorization(
            "/api/v1/profile", "GET", "user", []
        )
        assert result["authorized"] is True
        assert result["reason"] == "no_role_requirements"

    def test_validate_roles_single_role(self, middleware):
        """Test role validation with single required role"""
        # Test matching role
        result = middleware._validate_roles("admin", "admin", [])
        assert result["authorized"] is True
        assert result["matched_role"] == "admin"

        # Test non-matching role
        result = middleware._validate_roles("admin", "user", [])
        assert result["authorized"] is False
        assert result["required_roles"] == ["admin"]

    def test_validate_roles_multiple_roles(self, middleware):
        """Test role validation with multiple required roles"""
        required_roles = ["admin", "moderator"]

        # Test matching role
        result = middleware._validate_roles(required_roles, "admin", [])
        assert result["authorized"] is True
        assert result["matched_role"] == "admin"

        # Test non-matching role
        result = middleware._validate_roles(required_roles, "user", [])
        assert result["authorized"] is False
        assert result["required_roles"] == required_roles

    def test_validate_roles_with_user_roles_list(self, middleware):
        """Test role validation using user roles list"""
        required_roles = ["admin", "moderator"]
        user_roles = ["editor", "moderator"]

        # Test matching role in user_roles
        result = middleware._validate_roles(required_roles, "user", user_roles)
        assert result["authorized"] is True
        assert result["matched_role"] == "moderator"

        # Test no matching role
        result = middleware._validate_roles(
            required_roles, "user", ["editor", "viewer"]
        )
        assert result["authorized"] is False

    @pytest.mark.asyncio
    async def test_dispatch_successful_authorization(self, middleware, mock_request):
        """Test successful request processing with proper authorization"""
        mock_request.state.user_id = "123"
        mock_request.state.user_role = "admin"
        mock_request.state.user_roles = []

        call_next = AsyncMock(return_value=Response(content="success"))

        response = await middleware.dispatch(mock_request, call_next)

        assert response.status_code == 200
        call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_dispatch_insufficient_permissions(self, middleware, mock_request):
        """Test request rejection when user lacks required permissions"""
        mock_request.state.user_id = "123"
        mock_request.state.user_role = "user"
        mock_request.state.user_roles = []

        call_next = AsyncMock()

        response = await middleware.dispatch(mock_request, call_next)

        assert response.status_code == 403
        assert isinstance(response, JSONResponse)

        response_data = json.loads(response.body.decode())
        assert response_data["error"]["type"] == "authorization_error"
        assert "Insufficient permissions" in response_data["error"]["message"]
        assert response_data["error"]["correlation_id"] == "test-correlation-id"

        call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_unauthenticated_request(self, middleware, mock_request):
        """Test handling of unauthenticated requests"""
        mock_request.state.user_id = None  # No authenticated user

        call_next = AsyncMock(return_value=Response(content="success"))

        response = await middleware.dispatch(mock_request, call_next)

        # Should allow request to proceed (let auth middleware handle it)
        assert response.status_code == 200
        call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_dispatch_excluded_path_bypass(self, middleware, mock_request):
        """Test that excluded paths bypass authorization"""
        mock_request.url.path = "/health"

        call_next = AsyncMock(return_value=Response(content="health check"))

        response = await middleware.dispatch(mock_request, call_next)

        assert response.status_code == 200
        call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_dispatch_unexpected_exception(self, middleware, mock_request):
        """Test handling of unexpected exceptions during authorization"""
        mock_request.state.user_id = "123"
        mock_request.state.user_role = "admin"
        mock_request.state.user_roles = []  # Set to empty list instead of MagicMock

        call_next = AsyncMock(side_effect=Exception("Unexpected database error"))

        # Since authorization passes, the exception from call_next should be caught and return 500
        response = await middleware.dispatch(mock_request, call_next)

        assert response.status_code == 500
        response_data = response.body.decode("utf-8")
        assert "authorization_system_error" in response_data
        assert "Authorization system error" in response_data


class TestSetupUserRoleAuthorizationMiddleware:
    """Test cases for middleware setup function"""

    def test_setup_role_middleware_default_config(self):
        """Test middleware setup with default configuration"""
        app = FastAPI()

        # Should not raise an exception
        setup_user_role_authorization_middleware(app)

    def test_setup_role_middleware_custom_config(self):
        """Test middleware setup with custom configuration"""
        app = FastAPI()
        custom_requirements = {"/api/v1/admin": "admin"}  # type: ignore
        custom_excludes = ["/health", "/custom/path"]

        # Should not raise an exception
        setup_user_role_authorization_middleware(
            app,
            role_requirements=custom_requirements,
            exclude_paths=custom_excludes,
        )

    def test_setup_role_middleware_app_integration(self):
        """Test that middleware is properly added to FastAPI app"""
        app = FastAPI()

        # Count middleware before
        initial_middleware_count = len(app.user_middleware)

        setup_user_role_authorization_middleware(app)

        # Middleware count should increase
        assert len(app.user_middleware) > initial_middleware_count
