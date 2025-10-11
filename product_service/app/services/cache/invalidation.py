"""
Cache invalidation service for Product Service
"""

from typing import TYPE_CHECKING, Optional

try:
    from ...utils.logging import setup_product_logging

    logger = setup_product_logging("product_service_cache_invalidation")
except ImportError:
    import logging

    logger = logging.getLogger("product_service_cache_invalidation")

if TYPE_CHECKING:
    from ...middleware.monitoring.caching import ProductCachingMiddleware


class CacheInvalidationService:
    """Service for cache invalidation"""

    def __init__(self, cache_middleware: "ProductCachingMiddleware"):
        self.cache_middleware = cache_middleware

    async def invalidate_product_caches(self, product_id: Optional[int] = None) -> None:
        """Invalidate product-related caches"""
        patterns = [
            "method:GET|path:/api/v1/products",
            "method:GET|path:/api/v1/products/search",
            "method:GET|path:/api/v1/products/featured",
        ]

        total_invalidated: int = 0
        for pattern in patterns:
            count: int = await self.cache_middleware.invalidate_cache(pattern)
            total_invalidated += count

        logger.info(f"Invalidated {total_invalidated} product cache entries")

    async def invalidate_category_caches(
        self, category_id: Optional[int] = None
    ) -> None:
        """Invalidate category-related caches"""
        patterns = [
            "method:GET|path:/api/v1/categories",
            "method:GET|path:/api/v1/products",  # Products might be filtered by category
        ]

        total_invalidated: int = 0
        for pattern in patterns:
            count: int = await self.cache_middleware.invalidate_cache(pattern)
            total_invalidated += count

        logger.info(f"Invalidated {total_invalidated} category cache entries")

    async def clear_all_cache(self) -> None:
        """Clear entire cache"""
        await self.cache_middleware.invalidate_cache()
        logger.info("All cache cleared")
