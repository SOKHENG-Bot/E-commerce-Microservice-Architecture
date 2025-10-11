"""
Response caching middleware for Product Service
Provides in-memory caching for API responses
"""

import time
from typing import Any, Callable, Dict, List, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ...services.cache import InMemoryCache

try:
    from ...utils.logging import setup_product_logging

    logger = setup_product_logging("product_service_caching")
except ImportError:
    import logging

    logger = logging.getLogger("product_service_caching")


class ProductCachingMiddleware(BaseHTTPMiddleware):
    """
    In-memory response caching middleware for Product Service.

    Features:
    - In-memory caching (no external dependencies)
    - Configurable TTL per endpoint
    - Automatic cache cleanup
    - Cache key generation based on query parameters
    - Cache invalidation methods
    """

    def __init__(self, app: Any, max_cache_size: int = 1000, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self.cache = InMemoryCache(max_size=max_cache_size)

        # Cacheable paths and their TTL (seconds)
        self.cache_config: Dict[str, Dict[str, Dict[str, Any]]] = {
            "/api/v1/products": {
                "GET": {
                    "ttl": 300,  # 5 minutes
                    "vary_by": ["page", "size", "category_id", "is_active", "search"],
                },
            },
            "/api/v1/products/search": {
                "GET": {
                    "ttl": 180,  # 3 minutes
                    "vary_by": ["q", "page", "size", "category_id", "sort_by"],
                },
            },
            "/api/v1/products/featured": {
                "GET": {
                    "ttl": 600,  # 10 minutes
                    "vary_by": ["limit"],
                },
            },
            "/api/v1/categories": {
                "GET": {
                    "ttl": 600,  # 10 minutes
                    "vary_by": ["page", "size"],
                },
            },
            "/health": {
                "GET": {
                    "ttl": 30,  # 30 seconds
                    "vary_by": [],
                },
            },
        }

        # Status codes that should be cached
        self.cacheable_status_codes = {200, 201}

        # Headers to exclude from caching
        self.excluded_headers = {
            "set-cookie",
            "authorization",
            "x-request-id",
            "x-correlation-id",
            "date",
            "server",
        }

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Any:
        """Process caching middleware"""

        if not self.enabled:
            return await call_next(request)

        # Check if request is cacheable
        cache_config = self._get_cache_config(request)
        if not cache_config:
            return await call_next(request)

        # Generate cache key
        cache_key = self._generate_cache_key(request, cache_config["vary_by"])

        # Try to get from cache
        cached_response = await self.cache.get(cache_key)
        if cached_response:
            return self._create_response_from_cache(cached_response, cache_key)

        # Process request
        start_time = time.time()
        response = await call_next(request)
        processing_time = time.time() - start_time

        # Cache response if appropriate
        if self._should_cache_response(response):
            await self._cache_response(
                cache_key, response, cache_config["ttl"], processing_time
            )

        # Add cache headers
        response.headers["X-Cache-Status"] = "MISS"
        response.headers["X-Cache-Key"] = (
            cache_key[:32] + "..." if len(cache_key) > 32 else cache_key
        )

        return response

    def _get_cache_config(self, request: Request) -> Optional[Dict[str, Any]]:
        """Get cache configuration for request"""
        path = request.url.path
        method = request.method

        # Check exact path match first
        if path in self.cache_config and method in self.cache_config[path]:
            return self.cache_config[path][method]

        # Check path patterns
        for pattern, config in self.cache_config.items():
            if path.startswith(pattern) and method in config:
                return config[method]

        return None

    def _generate_cache_key(self, request: Request, vary_by_params: List[str]) -> str:
        """Generate cache key from request"""
        key_parts = [
            f"method:{request.method}",
            f"path:{request.url.path}",
        ]

        # Add query parameters that affect caching
        if vary_by_params:
            query_params: Dict[str, str] = {}
            for param in vary_by_params:
                value = request.query_params.get(param)
                if value is not None:
                    query_params[param] = value

            if query_params:
                sorted_params = sorted(query_params.items())
                params_str = "&".join(f"{k}={v}" for k, v in sorted_params)
                key_parts.append(f"params:{params_str}")

        return "|".join(key_parts)

    async def _cache_response(
        self, cache_key: str, response: Any, ttl: int, processing_time: float
    ) -> None:
        """Cache response data"""
        try:
            # Read response body
            response_body: bytes = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            # Prepare cache data
            cache_data: Dict[str, Any] = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body.decode("utf-8"),
                "cached_at": time.time(),
                "ttl": ttl,
                "processing_time": processing_time,
                "cache_key": cache_key,
            }

            # Remove excluded headers
            filtered_headers: Dict[str, Any] = {
                k: v
                for k, v in cache_data["headers"].items()
                if k.lower() not in self.excluded_headers
            }
            cache_data["headers"] = filtered_headers

            # Store in cache
            await self.cache.set(cache_key, cache_data, ttl)

            logger.debug(
                f"Response cached: {cache_key[:50]}... (TTL: {ttl}s, Size: {len(response_body)} bytes)"
            )

            # Recreate response body iterator
            response.body_iterator = self._create_body_iterator(response_body)

        except Exception as e:
            logger.error(f"Cache storage error: {e}")

    def _create_body_iterator(self, body: bytes):
        """Create async iterator for response body"""

        async def body_generator():
            yield body

        return body_generator()

    def _should_cache_response(self, response: Any) -> bool:
        """Determine if response should be cached"""
        return (
            response.status_code in self.cacheable_status_codes
            and response.headers.get("content-type", "").startswith("application/json")
        )

    def _create_response_from_cache(
        self, cached_data: Dict[str, Any], cache_key: str
    ) -> Response:
        """Create Response object from cached data"""

        # Add cache-specific headers
        headers: Dict[str, Any] = cached_data["headers"].copy()
        headers["X-Cache-Status"] = "HIT"
        headers["X-Cache-Age"] = str(int(time.time() - cached_data["cached_at"]))
        headers["X-Cache-TTL"] = str(cached_data["ttl"])
        headers["X-Cache-Key"] = (
            cache_key[:32] + "..." if len(cache_key) > 32 else cache_key
        )

        # Add performance metrics
        original_processing_time = cached_data.get("processing_time", 0)
        headers["X-Original-Processing-Time"] = f"{original_processing_time:.3f}s"
        if original_processing_time > 0:
            headers["X-Cache-Speedup"] = f"{original_processing_time / 0.001:.1f}x"

        return Response(
            content=cached_data["body"],
            status_code=cached_data["status_code"],
            headers=headers,
            media_type="application/json",
        )

    # Cache management methods
    async def invalidate_cache(self, pattern: Optional[str] = None) -> int:
        """Invalidate cache entries"""
        if pattern:
            # Simple pattern matching for cache keys
            keys_to_delete = [key for key in self.cache.cache.keys() if pattern in key]
            for key in keys_to_delete:
                await self.cache.delete(key)
            return len(keys_to_delete)
        else:
            await self.cache.clear()
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_stats()


def setup_product_caching_middleware(
    app: Any, max_cache_size: int = 1000, enabled: bool = True
) -> ProductCachingMiddleware:
    """Setup in-memory caching middleware for Product Service"""
    app.add_middleware(
        ProductCachingMiddleware, max_cache_size=max_cache_size, enabled=enabled
    )

    # Create instance for reference (middleware is already added to app)
    middleware = ProductCachingMiddleware(
        app=None,  # Not needed since it's already added
        max_cache_size=max_cache_size,
        enabled=enabled,
    )

    logger.info(
        "Product Service in-memory caching middleware configured",
        extra={
            "cache_enabled": enabled,
            "max_cache_size": max_cache_size,
            "cached_endpoints": len(middleware.cache_config),
        },
    )

    return middleware
