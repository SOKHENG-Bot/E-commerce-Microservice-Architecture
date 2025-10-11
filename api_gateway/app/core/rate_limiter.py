"""
Rate limiting using Redis for API Gateway
"""

import time
from typing import Any, Dict, Optional, Tuple, cast

import redis.asyncio as aioredis

from app.config.settings import GatewaySettings

# Import independent logging
from ..utils.logging import setup_api_gateway_logging

logger = setup_api_gateway_logging("api_gateway_rate_limiter")


class RateLimiter:
    """Redis-based rate limiter with sliding window"""

    def __init__(self, settings: GatewaySettings):
        self.settings = settings
        self.redis_client = None

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = aioredis.from_url(  # type: ignore[assignment]
                self.settings.REDIS_URL, encoding="utf-8", decode_responses=True
            )
            # Test connection
            await self.redis_client.ping()  # type: ignore[misc]
            logger.info("Rate limiter Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis for rate limiting: {e}")
            self.redis_client = None

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()

    async def is_allowed(
        self, key: str, limit: int, window: int, identifier: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limit
        Returns (allowed, info_dict)
        """
        if not self.redis_client or not self.settings.RATE_LIMIT_ENABLED:
            return True, {}

        try:
            current_time = int(time.time())
            pipe = self.redis_client.pipeline()

            # Sliding window rate limiting
            window_start = current_time - window

            # Remove expired entries
            pipe.zremrangebyscore(key, 0, window_start)  # type: ignore[misc]

            # Count current requests in window
            pipe.zcard(key)  # type: ignore[misc]

            # Add current request
            pipe.zadd(key, {f"{current_time}:{identifier or 'req'}": current_time})  # type: ignore[misc]

            # Set expiration
            pipe.expire(key, window + 10)  # type: ignore[misc]  # Extra buffer

            results = cast(list[int], await pipe.execute())
            current_count = int(results[1])  # Count after cleanup

            if current_count >= limit:
                # Remove the request we just added since it's not allowed
                await self.redis_client.zrem(  # type: ignore[misc]
                    key, f"{current_time}:{identifier or 'req'}"
                )

                # Calculate reset time
                oldest_request = cast(
                    list[tuple[str, float]],
                    await self.redis_client.zrange(key, 0, 0, withscores=True),  # type: ignore[misc]
                )
                reset_time = (
                    int(oldest_request[0][1]) + window
                    if oldest_request
                    else current_time + window
                )

                return False, {
                    "limit": limit,
                    "remaining": 0,
                    "reset_time": reset_time,
                    "current_count": current_count,
                }

            return True, {
                "limit": limit,
                "remaining": limit - current_count - 1,
                "reset_time": current_time + window,
                "current_count": current_count + 1,
            }

        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # On error, allow the request (fail open)
            return True, {}

    async def check_global_rate_limit(
        self, client_ip: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check global rate limit by IP"""
        return await self.is_allowed(
            key=f"rate_limit:global:{client_ip}",
            limit=self.settings.RATE_LIMIT_REQUESTS,
            window=self.settings.RATE_LIMIT_WINDOW,
            identifier=client_ip,
        )

    async def check_user_rate_limit(self, user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Check authenticated user rate limit"""
        return await self.is_allowed(
            key=f"rate_limit:user:{user_id}",
            limit=self.settings.RATE_LIMIT_PER_USER_REQUESTS,
            window=self.settings.RATE_LIMIT_PER_USER_WINDOW,
            identifier=user_id,
        )
