from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

import redis.asyncio as redis
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from fastapi import FastAPI

from user_service.app.core.settings import get_settings

settings = get_settings()


class UserServiceRateLimiter:
    """Class to handle rate limiting logic using Redis."""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = getattr(settings, "RATE_LIMIT_ENABLED", True)
        self.limits = {
            "general": {"requests": 100, "window": 3600},  # 100 req/hour
            "auth": {"requests": 20, "window": 3600},  # 20 req/hour
            "register": {"requests": 5, "window": 3600},  # 5 req/hour
            "password": {"requests": 3, "window": 3600},  # 3 req/hour
            "user_ops": {"requests": 50, "window": 3600},  # 50 req/hour
        }

    async def initialize(self):
        """Initialize Redis client for rate limiting."""

        try:
            redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/1")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)  # type: ignore[misc]
            await self.redis_client.ping()  # type: ignore[misc]
            return True
        except Exception:
            self.redis_client = None
            return False

    async def is_allowed(
        self, key: str, limit_type: str = "general"
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if a request is allowed under the rate limit."""

        if not self.enabled or not self.redis_client:
            return True, {}

        config = self.limits.get(limit_type, self.limits["general"])
        limit = config["requests"]
        window = config["window"]

        try:
            current_time = int(time.time())
            window_start = current_time - window

            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)  # type: ignore[misc]
            pipe.zcard(key)  # type: ignore[misc]
            pipe.zadd(key, {f"{current_time}": current_time})  # type: ignore[misc]
            pipe.expire(key, window + 60)  # type: ignore[misc]

            results = await pipe.execute()  # type: ignore[misc]
            current_count = int(results[1])  # type: ignore[misc]

            if current_count >= limit:
                await self.redis_client.zrem(key, f"{current_time}")  # type: ignore[misc]

                return False, {
                    "limit": limit,
                    "remaining": 0,
                    "reset_time": current_time + window,
                    "current_count": current_count,
                }

            return True, {
                "limit": limit,
                "remaining": limit - current_count - 1,
                "reset_time": current_time + window,
                "current_count": current_count + 1,
            }

        except Exception:
            return True, {}

    def get_limit_type(self, path: str, method: str) -> str:
        """Determine the limit type based on request path and method."""

        if "/auth/register" in path:
            return "register"
        elif any(
            x in path
            for x in [
                "/auth/forgot-password",
                "/auth/reset-password",
                "/auth/change-password",
            ]
        ):
            return "password"
        elif "/auth/" in path:
            return "auth"
        elif any(x in path for x in ["/users/", "/profiles/", "/addresses/"]):
            return "user_ops"
        else:
            return "general"

    async def close(self):
        """Close the Redis client connection."""

        if self.redis_client:
            await self.redis_client.close()


class UserServiceRateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting on incoming requests."""

    def __init__(self, app: FastAPI, rate_limiter: UserServiceRateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.exempt_paths = {
            "/health",
            "/health/detailed",
            "/docs",
            "/openapi.json",
            "/redoc",
        }

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[misc]
        """Middleware to enforce rate limiting on incoming requests."""

        path = request.url.path
        if any(path.startswith(exempt) for exempt in self.exempt_paths):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        user_id = getattr(request.state, "user_id", None)

        if user_id:
            key = f"rate_limit:user:{user_id}"
        else:
            key = f"rate_limit:ip:{client_ip}"

        limit_type = self.rate_limiter.get_limit_type(path, request.method)

        allowed, info = await self.rate_limiter.is_allowed(
            f"{key}:{limit_type}", limit_type
        )

        if not allowed:
            return Response(
                content='{"detail": "Rate limit exceeded"}',
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "X-RateLimit-Limit": str(info.get("limit", 0)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info.get("reset_time", 0)),
                    "Retry-After": str(60),
                },
            )

        response = await call_next(request)

        if info:
            response.headers["X-RateLimit-Limit"] = str(info.get("limit", 0))
            response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(info.get("reset_time", 0))

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request headers or connection info."""

        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"
