"""
Unit tests for User Service API Versioning Middleware
Tests version extraction, validation, and response formatting.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from user_service.app.middleware.api.versioning import (
    APIVersion,
    APIVersioningMiddleware,
    get_api_version,
    max_version,
    min_version,
    supports_async_operations,
    supports_bulk_operations,
    version_deprecated,
)


class TestAPIVersion:
    """Test cases for APIVersion class"""

    def test_version_creation(self):
        """Test APIVersion object creation"""
        version = APIVersion(1, 2, 3)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert str(version) == "v1.2.3"
        assert version.to_header_value() == "1.2"

    def test_version_from_string(self):
        """Test parsing version from string"""
        # Test various formats
        assert APIVersion.from_string("v1.2.3") == APIVersion(1, 2, 3)
        assert APIVersion.from_string("1.2.3") == APIVersion(1, 2, 3)
        assert APIVersion.from_string("v2.0") == APIVersion(2, 0, 0)
        assert APIVersion.from_string("3") == APIVersion(3, 0, 0)

    def test_version_compatibility(self):
        """Test version compatibility checking"""
        v1_0 = APIVersion(1, 0, 0)
        v1_1 = APIVersion(1, 1, 0)
        v2_0 = APIVersion(2, 0, 0)

        assert v1_0.is_compatible_with(v1_1)
        assert v1_1.is_compatible_with(v1_0)
        assert not v1_0.is_compatible_with(v2_0)
        assert not v2_0.is_compatible_with(v1_0)


class TestAPIVersioningMiddleware:
    """Test cases for API versioning middleware"""

    @pytest.fixture
    def middleware(self):
        """Create API versioning middleware instance"""
        app = FastAPI()
        return APIVersioningMiddleware(
            app=app, default_version="1.0", supported_versions=["1.0", "1.1"]
        )

    @pytest.fixture
    def mock_request(self):
        """Create mock request"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/users"
        request.method = "GET"
        request.headers = {}
        request.state = MagicMock()
        return request

    def test_extract_version_from_accept_header(self, middleware, mock_request):
        """Test version extraction from Accept header"""
        # Test vendor media type
        mock_request.headers = {"Accept": "application/vnd.userservice.v1.1+json"}
        version = middleware._extract_version(mock_request)
        assert version == APIVersion(1, 1, 0)

        # Test without vendor prefix
        mock_request.headers = {"Accept": "application/vnd.userservice.v1.0+json"}
        version = middleware._extract_version(mock_request)
        assert version == APIVersion(1, 0, 0)

    def test_extract_version_from_x_api_version_header(self, middleware, mock_request):
        """Test version extraction from X-API-Version header"""
        mock_request.headers = {"X-API-Version": "1.1"}
        version = middleware._extract_version(mock_request)
        assert version == APIVersion(1, 1, 0)

    def test_extract_version_from_path(self, middleware, mock_request):
        """Test version extraction from URL path"""
        mock_request.url.path = "/api/v1.1/users"
        version = middleware._extract_version(mock_request)
        assert version == APIVersion(1, 1, 0)

        mock_request.url.path = "/api/v2/users"
        version = middleware._extract_version(mock_request)
        assert version == APIVersion(2, 0, 0)

    def test_extract_version_default(self, middleware, mock_request):
        """Test default version when no version specified"""
        mock_request.headers = {}
        version = middleware._extract_version(mock_request)
        assert version == APIVersion(1, 0, 0)

    def test_is_supported_version(self, middleware):
        """Test version support validation"""
        assert middleware._is_supported_version(APIVersion(1, 0, 0))
        assert middleware._is_supported_version(APIVersion(1, 1, 0))
        assert not middleware._is_supported_version(APIVersion(2, 0, 0))

    @pytest.mark.asyncio
    async def test_dispatch_supported_version(self, middleware, mock_request):
        """Test successful request processing with supported version"""
        mock_request.headers = {"Accept": "application/vnd.userservice.v1.1+json"}

        call_next = AsyncMock(return_value=Response(content='{"data": "test"}'))

        response = await middleware.dispatch(mock_request, call_next)

        assert response.status_code == 200
        assert mock_request.state.api_version == APIVersion(1, 1, 0)
        assert response.headers["X-API-Version"] == "1.1"
        assert "X-Supported-Versions" in response.headers

    @pytest.mark.asyncio
    async def test_dispatch_unsupported_version(self, middleware, mock_request):
        """Test rejection of unsupported API version"""
        mock_request.headers = {"X-API-Version": "2.0"}

        call_next = AsyncMock()

        response = await middleware.dispatch(mock_request, call_next)

        assert response.status_code == 400
        assert isinstance(response, JSONResponse)

        response_data = json.loads(response.body.decode())
        assert "Unsupported API version" in response_data["detail"]
        assert "supported_versions" in response_data

        call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_deprecated_version(self, middleware, mock_request):
        """Test handling of deprecated API version"""
        # Create middleware with deprecated version
        app = FastAPI()
        deprecated_middleware = APIVersioningMiddleware(
            app=app, default_version="1.0", supported_versions=["1.0", "1.1"]
        )
        deprecated_middleware.deprecated_versions = {"1.0": "Version 1.0 is deprecated"}

        mock_request.headers = {"X-API-Version": "1.0"}

        call_next = AsyncMock(return_value=Response(content='{"data": "test"}'))

        response = await deprecated_middleware.dispatch(mock_request, call_next)

        assert response.status_code == 200
        assert "X-API-Deprecation-Warning" in response.headers
        assert (
            "Version 1.0 is deprecated" in response.headers["X-API-Deprecation-Warning"]
        )


class TestVersionUtilities:
    """Test cases for version utility functions"""

    def test_get_api_version(self):
        """Test get_api_version utility function"""
        request = MagicMock(spec=Request)
        request.state.api_version = APIVersion(1, 1, 0)

        version = get_api_version(request)
        assert version == APIVersion(1, 1, 0)

    def test_get_api_version_default(self):
        """Test get_api_version with no version set"""
        request = MagicMock(spec=Request)
        request.state.api_version = None

        version = get_api_version(request)
        assert version == APIVersion(1, 0, 0)

    def test_supports_bulk_operations(self):
        """Test bulk operations support check"""
        # v1.1+ supports bulk operations
        request_v11 = MagicMock(spec=Request)
        request_v11.state.api_version = APIVersion(1, 1, 0)
        assert supports_bulk_operations(request_v11)

        # v1.0 does not support bulk operations
        request_v10 = MagicMock(spec=Request)
        request_v10.state.api_version = APIVersion(1, 0, 0)
        assert not supports_bulk_operations(request_v10)

    def test_supports_async_operations(self):
        """Test async operations support check"""
        # Only v2.0+ supports async operations
        request_v11 = MagicMock(spec=Request)
        request_v11.state.api_version = APIVersion(1, 1, 0)
        assert not supports_async_operations(request_v11)

        request_v20 = MagicMock(spec=Request)
        request_v20.state.api_version = APIVersion(2, 0, 0)
        assert supports_async_operations(request_v20)


class TestVersionDecorators:
    """Test cases for version decorator functions"""

    def test_version_deprecated_decorator(self):
        """Test version deprecated decorator"""

        @version_deprecated("1.0")
        def test_function():
            return "test"

        assert hasattr(test_function, "_deprecated_versions")
        assert "1.0" in test_function._deprecated_versions

    def test_min_version_decorator(self):
        """Test minimum version decorator"""

        @min_version("1.1")
        def test_function():
            return "test"

        assert test_function._min_version == "1.1"

    def test_max_version_decorator(self):
        """Test maximum version decorator"""

        @max_version("2.0")
        def test_function():
            return "test"

        assert test_function._max_version == "2.0"
