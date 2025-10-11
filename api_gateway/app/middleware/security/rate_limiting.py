"""
Rate limiting middleware for API Gateway
"""

from typing import Awaitable, Callable, Optional

from fastapi import HTTPException, Request, Response, status

from app.config.settings import GatewaySettings
from app.core.rate_limiter import RateLimiter

# Import independent logging
from app.utils.logging import setup_api_gateway_logging

logger = setup_api_gateway_logging("api_gateway_rate_limiting")


class RateLimitingMiddleware:
    """Rate limiting middleware using Redis"""

    def __init__(self, settings: GatewaySettings, rate_limiter: RateLimiter):
        self.settings = settings
        self.rate_limiter = rate_limiter

        # Exempt endpoints from rate limiting
        self.exempt_endpoints = {
            "/health",
            "/health/detailed",
            "/health/ready",
            "/health/live",
        }

    async def __call__(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process rate limiting middleware"""
        path = request.url.path

        # Skip rate limiting for exempt endpoints
        if path in self.exempt_endpoints or not self.settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Get client identifier
        client_ip = self._get_client_ip(request)
        user_id = getattr(request.state, "user_id", None)

        try:
            # Check rate limits
            await self._check_rate_limits(client_ip, user_id)

            # Process request
            response = await call_next(request)

            # Add rate limit headers to response
            self._add_rate_limit_headers(response, client_ip, user_id)

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limiting middleware error: {e}")
            # On error, allow request (fail open)
            return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        # Check for forwarded headers (from load balancer/proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"

    async def _check_rate_limits(self, client_ip: str, user_id: Optional[str]):
        """Check both global and user-specific rate limits"""
        # Check global rate limit (by IP)
        allowed, info = await self.rate_limiter.check_global_rate_limit(client_ip)
        if not allowed:
            logger.warning(
                "Global rate limit exceeded",
                extra={
                    "client_ip": client_ip,
                    "limit": info.get("limit"),
                    "current_count": info.get("current_count"),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(info.get("limit", 0)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info.get("reset_time", 0)),
                },
            )

        # Check user-specific rate limit if authenticated
        if user_id:
            allowed, user_info = await self.rate_limiter.check_user_rate_limit(user_id)
            if not allowed:
                logger.warning(
                    "User rate limit exceeded",
                    extra={
                        "user_id": user_id,
                        "limit": user_info.get("limit"),
                        "current_count": user_info.get("current_count"),
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="User rate limit exceeded",
                    headers={
                        "X-RateLimit-User-Limit": str(user_info.get("limit", 0)),
                        "X-RateLimit-User-Remaining": "0",
                        "X-RateLimit-User-Reset": str(user_info.get("reset_time", 0)),
                    },
                )

    def _add_rate_limit_headers(
        self, response: Response, client_ip: str, user_id: Optional[str]
    ):
        """Add rate limit headers to response"""
        # This would require another Redis call to get current limits
        # For performance, we could cache this information or add it during the check
        pass
