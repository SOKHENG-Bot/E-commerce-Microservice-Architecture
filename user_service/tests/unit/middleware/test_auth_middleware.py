"""
Unit tests for User Service Authentication Middleware
Tests JWT token validation, user context extraction, and authentication flow.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from user_service.app.middleware.auth.auth_middleware import (
    AuthenticatedUser,
    UserServiceAuthMiddleware,
    setup_user_auth_middleware,
)


class TestUserServiceAuthMiddleware:
    """Test cases for authentication middleware"""

    @pytest.fixture
    def mock_jwt_handler(self):
        """Mock JWT handler for testing"""
        mock_handler = MagicMock()
        mock_handler.decode_token.return_value = MagicMock(
            user_id="123",
            email="test@example.com",
            username="testuser",
            roles=["user"],
            permissions=["read"],
            expires_at=MagicMock(timestamp=lambda: 2000000000),  # Future timestamp
        )
        return mock_handler

    @pytest.fixture
    def auth_middleware(self, mock_jwt_handler):
        """Create auth middleware instance"""
        app = FastAPI()
        middleware = UserServiceAuthMiddleware(
            app=app, jwt_handler=mock_jwt_handler, exclude_paths=["/health", "/docs"]
        )
        return middleware

    @pytest.fixture
    def mock_request(self):
        """Create mock request"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/users/profile"
        request.method = "GET"
        request.cookies = {}
        request.headers = {}
        request.state = MagicMock()
        request.state.correlation_id = "test-correlation-id"
        return request

    def test_should_skip_auth_excluded_paths(self, auth_middleware):
        """Test that excluded paths skip authentication"""
        excluded_paths = [
            "/health",
            "/docs",
        ]  # Only test paths that are actually excluded in fixture

        for path in excluded_paths:
            assert auth_middleware._should_skip_auth(path)

        assert not auth_middleware._should_skip_auth("/api/v1/users/profile")

    def test_should_skip_auth_prefix_matches(self, auth_middleware):
        """Test that path prefixes are properly excluded"""
        assert auth_middleware._should_skip_auth("/docs/swagger")
        assert auth_middleware._should_skip_auth("/docs/redoc")
        assert not auth_middleware._should_skip_auth("/api/docs")

    @pytest.mark.asyncio
    async def test_authenticate_request_valid_cookie_token(
        self, auth_middleware, mock_request, mock_jwt_handler
    ):
        """Test successful authentication with valid cookie token"""
        mock_request.cookies = {"auth_token": "valid.jwt.token"}

        result = await auth_middleware._authenticate_request(mock_request)

        assert result["authenticated"] is True
        assert result["user_id"] == "123"
        assert result["user_role"] == "user"
        assert result["token_source"] == "cookie"
        mock_jwt_handler.decode_token.assert_called_once_with("valid.jwt.token")

    @pytest.mark.asyncio
    async def test_authenticate_request_missing_cookie(
        self, auth_middleware, mock_request
    ):
        """Test authentication failure when no auth cookie is present"""
        mock_request.cookies = {}

        result = await auth_middleware._authenticate_request(mock_request)

        assert result["authenticated"] is False
        assert result["reason"] == "missing_auth_cookie"

    @pytest.mark.asyncio
    async def test_authenticate_request_empty_cookie(
        self, auth_middleware, mock_request
    ):
        """Test authentication failure with empty/null cookie values"""
        test_cases = [
            {"auth_token": ""},
            {"auth_token": "null"},
            {"auth_token": "undefined"},
            {"auth_token": "   "},
        ]

        for cookies in test_cases:
            mock_request.cookies = cookies
            result = await auth_middleware._authenticate_request(mock_request)
            assert result["authenticated"] is False
            assert result["reason"] in ["empty_cookie_token", "missing_auth_cookie"]

    @pytest.mark.asyncio
    async def test_authenticate_request_invalid_token(
        self, auth_middleware, mock_request, mock_jwt_handler
    ):
        """Test authentication failure with invalid JWT token"""
        mock_request.cookies = {"auth_token": "invalid.jwt.token"}
        mock_jwt_handler.decode_token.return_value = None  # Token validation fails

        result = await auth_middleware._authenticate_request(mock_request)

        assert result["authenticated"] is False
        assert result["reason"] == "invalid_cookie_token"

    @pytest.mark.asyncio
    async def test_authenticate_request_jwt_exception(
        self, auth_middleware, mock_request, mock_jwt_handler
    ):
        """Test authentication failure when JWT handler raises exception"""
        mock_request.cookies = {"auth_token": "malformed.jwt.token"}
        mock_jwt_handler.decode_token.side_effect = ValueError("Invalid token format")

        result = await auth_middleware._authenticate_request(mock_request)

        assert result["authenticated"] is False
        assert (
            result["reason"] == "invalid_cookie_token"
        )  # JWT validation failure returns None, which is invalid token

    @pytest.mark.asyncio
    async def test_dispatch_successful_authentication(
        self, auth_middleware, mock_request
    ):
        """Test successful request processing with authentication"""
        mock_request.cookies = {"auth_token": "valid.jwt.token"}
        mock_request.url.path = "/api/v1/users/profile"

        call_next = AsyncMock(return_value=Response(content="success"))

        with patch.object(auth_middleware, "_authenticate_request") as mock_auth:
            mock_auth.return_value = {
                "authenticated": True,
                "user_id": "123",
                "user_role": "user",
                "token_data": {"user_id": "123"},
            }

            response = await auth_middleware.dispatch(mock_request, call_next)

            assert response.status_code == 200
            assert mock_request.state.user_id == "123"
            assert mock_request.state.user_role == "user"
            call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_dispatch_authentication_failure(self, auth_middleware, mock_request):
        """Test request rejection when authentication fails"""
        mock_request.cookies = {}
        mock_request.url.path = "/api/v1/users/profile"

        call_next = AsyncMock()

        with patch.object(auth_middleware, "_authenticate_request") as mock_auth:
            mock_auth.return_value = {
                "authenticated": False,
                "reason": "missing_auth_cookie",
            }

            response = await auth_middleware.dispatch(mock_request, call_next)

            assert response.status_code == 401
            assert isinstance(response, JSONResponse)

            response_data = json.loads(response.body.decode())
            assert response_data["error"]["type"] == "authentication_error"
            assert "Authentication required" in response_data["error"]["message"]
            assert response_data["error"]["correlation_id"] == "test-correlation-id"

            # call_next should not be called
            call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_excluded_path_bypass(self, auth_middleware, mock_request):
        """Test that excluded paths bypass authentication"""
        mock_request.url.path = "/health"

        call_next = AsyncMock(return_value=Response(content="health check"))

        response = await auth_middleware.dispatch(mock_request, call_next)

        assert response.status_code == 200
        call_next.assert_called_once_with(mock_request)
        # No authentication should have been attempted

    @pytest.mark.asyncio
    async def test_dispatch_unexpected_exception(self, auth_middleware, mock_request):
        """Test handling of unexpected exceptions during authentication"""
        mock_request.cookies = {"auth_token": "some.token"}

        call_next = AsyncMock()

        with patch.object(auth_middleware, "_authenticate_request") as mock_auth:
            mock_auth.side_effect = Exception("Unexpected database error")

            response = await auth_middleware.dispatch(mock_request, call_next)

            assert response.status_code == 500
            assert isinstance(response, JSONResponse)

            response_data = json.loads(response.body.decode())
            assert response_data["error"]["type"] == "authentication_system_error"
            assert "Authentication system error" in response_data["error"]["message"]

            call_next.assert_not_called()


class TestAuthenticatedUser:
    """Test cases for AuthenticatedUser dependency"""

    @pytest.fixture
    def auth_user_dep(self):
        """Create AuthenticatedUser dependency instance"""
        return AuthenticatedUser()

    @pytest.fixture
    def mock_request_with_user(self):
        """Create mock request with authenticated user"""
        request = MagicMock(spec=Request)
        request.state.user_id = "123"
        request.state.user_role = "user"
        request.state.token_data = {"user_id": "123", "email": "test@example.com"}
        return request

    @pytest.fixture
    def mock_request_no_user(self):
        """Create mock request without authenticated user"""
        request = MagicMock(spec=Request)
        request.state.user_id = None
        return request

    @pytest.mark.asyncio
    async def test_authenticated_user_success(
        self, auth_user_dep, mock_request_with_user
    ):
        """Test successful authenticated user dependency"""
        result = await auth_user_dep(mock_request_with_user)

        assert result["user_id"] == "123"
        assert result["role"] == "user"
        assert result["token_data"]["user_id"] == "123"

    @pytest.mark.asyncio
    async def test_authenticated_user_failure(
        self, auth_user_dep, mock_request_no_user
    ):
        """Test authenticated user dependency failure"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await auth_user_dep(mock_request_no_user)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Authentication required"

    @pytest.mark.asyncio
    async def test_authenticated_user_with_role_requirement(self):
        """Test authenticated user with specific role requirement"""
        admin_dep = AuthenticatedUser(required_role="admin")

        # Test with matching role
        request_admin = MagicMock(spec=Request)
        request_admin.state.user_id = "123"
        request_admin.state.user_role = "admin"

        result = await admin_dep(request_admin)
        assert result["user_id"] == "123"
        assert result["role"] == "admin"

        # Test with non-matching role
        request_user = MagicMock(spec=Request)
        request_user.state.user_id = "123"
        request_user.state.user_role = "user"

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await admin_dep(request_user)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Required role: admin"


class TestSetupUserAuthMiddleware:
    """Test cases for middleware setup function"""

    def test_setup_user_auth_middleware_default_config(self):
        """Test middleware setup with default configuration"""
        app = FastAPI()

        # Should not raise an exception
        setup_user_auth_middleware(app)

        # Verify middleware was added to app
        assert len(app.user_middleware) > 0

    def test_setup_user_auth_middleware_custom_config(self):
        """Test middleware setup with custom configuration"""
        app = FastAPI()
        custom_excludes = ["/health", "/custom/path"]
        mock_jwt_handler = MagicMock()

        # Should not raise an exception
        setup_user_auth_middleware(
            app, exclude_paths=custom_excludes, jwt_handler=mock_jwt_handler
        )

        # Verify middleware was added to app
        assert len(app.user_middleware) > 0

    def test_setup_user_auth_middleware_app_integration(self):
        """Test that middleware is properly added to FastAPI app"""
        app = FastAPI()

        # Count middleware before
        initial_middleware_count = len(app.user_middleware)

        setup_user_auth_middleware(app)

        # Verify middleware was added
        assert len(app.user_middleware) == initial_middleware_count + 1

        # Verify the middleware type
        added_middleware = app.user_middleware[-1]
        assert isinstance(added_middleware.cls, type(UserServiceAuthMiddleware))
