"""
In-memory cache implementation for Product Service
"""

import asyncio
import time
from typing import Any, Dict, Optional

try:
    from ...utils.logging import setup_product_logging

    logger = setup_product_logging("product_service_cache")
except ImportError:
    import logging

    logger = logging.getLogger("product_service_cache")


class InMemoryCache:
    """Simple in-memory cache with TTL support"""

    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self._cleanup_task: Optional[asyncio.Task[Any]] = None

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() < entry["expires_at"]:
                return entry["value"]
            else:
                # Expired, remove it
                del self.cache[key]
        return None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in cache with TTL"""
        # Clean up if cache is getting too large
        if len(self.cache) >= self.max_size:
            await self._cleanup_expired()

        self.cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl,
            "created_at": time.time(),
        }

    async def delete(self, key: str) -> None:
        """Delete key from cache"""
        self.cache.pop(key, None)

    async def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()

    async def _cleanup_expired(self) -> None:
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self.cache.items()
            if current_time >= entry["expires_at"]
        ]
        for key in expired_keys:
            del self.cache[key]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_entries = len(self.cache)
        if total_entries == 0:
            return {"entries": 0, "hit_rate": 0}

        current_time = time.time()
        expired_count = sum(
            1 for entry in self.cache.values() if current_time >= entry["expires_at"]
        )

        return {
            "entries": total_entries,
            "expired_entries": expired_count,
            "active_entries": total_entries - expired_count,
            "max_size": self.max_size,
        }
