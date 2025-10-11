"""
User service middleware package.
Contains organized middleware components by functional categories.
"""

# API middleware
from .api.versioning import (
    APIVersion,
    APIVersioningMiddleware,
    VersionedResponse,
    get_api_version,
    max_version,
    min_version,
    version_deprecated,
)

# Security middleware
from .security.rate_limiting import (
    UserServiceRateLimiter,
    UserServiceRateLimitingMiddleware,
)

__all__ = [
    # Security
    "UserServiceRateLimitingMiddleware",
    "UserServiceRateLimiter",
    # API
    "APIVersion",
    "APIVersioningMiddleware",
    "get_api_version",
    "version_deprecated",
    "min_version",
    "max_version",
    "VersionedResponse",
]
