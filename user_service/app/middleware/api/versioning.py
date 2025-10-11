"""
API Versioning middleware and utilities for User Service
Supports header-based and path-based versioning
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from fastapi import FastAPI


class APIVersion:
    """API Version representation"""

    def __init__(self, major: int, minor: int = 0, patch: int = 0):
        self.major = major
        self.minor = minor
        self.patch = patch

    def __str__(self) -> str:
        return f"v{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:
        return f"APIVersion({self.major}, {self.minor}, {self.patch})"

    def __eq__(self, other: object) -> bool:
        """Check equality with another APIVersion"""
        if not isinstance(other, APIVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) == (
            other.major,
            other.minor,
            other.patch,
        )

    def __hash__(self) -> int:
        """Make APIVersion hashable"""
        return hash((self.major, self.minor, self.patch))

    def to_header_value(self) -> str:
        return f"{self.major}.{self.minor}"

    @classmethod
    def from_string(cls, version_str: str) -> "APIVersion":
        """Parse version string like 'v1.2' or '1.2.3'"""
        version_str = version_str.lstrip("v")
        parts = version_str.split(".")

        major = int(parts[0]) if parts else 1
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0

        return cls(major, minor, patch)

    def is_compatible_with(self, other: "APIVersion") -> bool:
        """Check if this version is compatible with another"""
        # Same major version is compatible
        return self.major == other.major


class APIVersioningMiddleware(BaseHTTPMiddleware):
    """Middleware to handle API versioning"""

    def __init__(
        self,
        app: FastAPI,
        default_version: str = "1.0",
        supported_versions: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.default_version = APIVersion.from_string(default_version)
        self.supported_versions = [
            APIVersion.from_string(v) for v in (supported_versions or ["1.0", "1.1"])
        ]

        # Version deprecation warnings
        self.deprecated_versions = {
            "1.0": "API v1.0 is deprecated. Please upgrade to v1.1 or higher."
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[misc]
        """Process API versioning"""
        # Extract version from request
        version = self._extract_version(request)

        # Validate version
        if not self._is_supported_version(version):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": "Unsupported API version",
                    "supported_versions": ["1.0", "1.1"],
                },
            )

        # Set version in request state
        request.state.api_version = version

        # Process request
        response = await call_next(request)  # type: ignore[misc]

        # Add version headers to response
        response.headers["X-API-Version"] = version.to_header_value()  # type: ignore[misc]
        response.headers["X-Supported-Versions"] = ", ".join(  # type: ignore[misc]
            v.to_header_value() for v in self.supported_versions
        )

        # Add deprecation warning if needed
        version_str = version.to_header_value()
        if version_str in self.deprecated_versions:
            response.headers["X-API-Deprecation-Warning"] = self.deprecated_versions[  # type: ignore[misc]
                version_str
            ]

        return response  # type: ignore[misc]

    def _extract_version(self, request: Request) -> APIVersion:
        """Extract API version from request"""
        # 1. Check Accept header (preferred)
        accept_header = request.headers.get("Accept", "")
        if "application/vnd.userservice.v" in accept_header:
            # Format: application/vnd.userservice.v1.1+json
            try:
                version_part = accept_header.split("application/vnd.userservice.v")[1]
                version_str = version_part.split("+")[0]
                return APIVersion.from_string(version_str)
            except (IndexError, ValueError):
                pass

        # 2. Check X-API-Version header
        version_header = request.headers.get("X-API-Version")
        if version_header:
            try:
                return APIVersion.from_string(version_header)
            except ValueError:
                pass

        # 3. Check path prefix (e.g., /api/v1/...)
        path = request.url.path
        if path.startswith("/api/v"):
            try:
                version_part = path.split("/api/v")[1].split("/")[0]
                return APIVersion.from_string(version_part)
            except (IndexError, ValueError):
                pass

        # 4. Default version
        return self.default_version

    def _is_supported_version(self, version: APIVersion) -> bool:
        """Check if version is supported"""
        return any(version.is_compatible_with(v) for v in self.supported_versions)


def get_api_version(request: Request) -> APIVersion:
    """Get API version from request state"""
    api_version = getattr(request.state, "api_version", None)
    return api_version if api_version is not None else APIVersion(1, 0)


def version_deprecated(version: str) -> Callable[[Any], Any]:
    """Decorator to mark endpoints as deprecated for specific versions"""

    def decorator(func: Any) -> Any:
        func._deprecated_versions = getattr(func, "_deprecated_versions", [])  # type: ignore[misc]
        func._deprecated_versions.append(version)  # type: ignore[misc]
        return func  # type: ignore[misc]

    return decorator  # type: ignore[misc]


def min_version(version: str) -> Callable[[Any], Any]:
    """Decorator to set minimum version requirement for a route"""

    def decorator(func: Any) -> Any:
        func._min_version = version  # type: ignore[misc]
        return func  # type: ignore[misc]

    return decorator  # type: ignore[misc]


def max_version(version: str) -> Callable[[Any], Any]:
    """Decorator to set maximum version requirement for a route"""

    def decorator(func: Any) -> Any:
        func._max_version = version  # type: ignore[misc]
        return func  # type: ignore[misc]

    return decorator  # type: ignore[misc]


# Version-specific endpoint utilities
class VersionedResponse:
    """Helper for creating version-specific responses"""

    @staticmethod
    def create_response(request: Request, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create version-appropriate response"""
        version = get_api_version(request)

        if version.major >= 1 and version.minor >= 1:
            # v1.1+ includes additional metadata
            return {
                "data": data,
                "meta": {
                    "version": version.to_header_value(),
                    "timestamp": int(time.time()),
                    "request_id": getattr(request.state, "request_id", "unknown"),
                },
            }
        else:
            # v1.0 returns data directly for compatibility
            return data


# API Version compatibility helpers
def supports_bulk_operations(request: Request) -> bool:
    """Check if current API version supports bulk operations"""
    version = get_api_version(request)
    return version.major >= 1 and version.minor >= 1


def supports_async_operations(request: Request) -> bool:
    """Check if current API version supports async operations"""
    version = get_api_version(request)
    return version.major >= 2  # Future version
