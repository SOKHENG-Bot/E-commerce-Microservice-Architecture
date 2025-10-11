"""
Service registry and discovery for API Gateway
"""

import asyncio
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional

import httpx

from app.config.settings import GatewaySettings

# Import independent logging
from ..utils.logging import setup_api_gateway_logging

logger = setup_api_gateway_logging("api_gateway_registry")


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class ServiceInfo:
    """Service information and health status with load balancing support"""

    def __init__(self, name: str, urls: list[str], health_urls: list[str]):
        self.name = name
        self.urls = urls  # List of service URLs for load balancing
        self.health_urls = health_urls  # Corresponding health check URLs
        self.current_url_index = 0  # For round-robin selection
        self.status = ServiceStatus.UNKNOWN
        self.last_check: Optional[datetime] = None
        self.response_time: Optional[float] = None
        self.error_count = 0
        self.consecutive_failures = 0
        self.circuit_open = False
        self.circuit_open_until: Optional[datetime] = None

    def get_next_url(self) -> str:
        """Get next URL using round-robin algorithm"""
        if not self.urls:
            raise ValueError(f"No URLs available for service {self.name}")

        url = self.urls[self.current_url_index]
        self.current_url_index = (self.current_url_index + 1) % len(self.urls)
        return url

    def get_health_url(self, url: str) -> Optional[str]:
        """Get corresponding health URL for a service URL"""
        try:
            index = self.urls.index(url)
            return self.health_urls[index] if index < len(self.health_urls) else None
        except ValueError:
            return None

    def is_available(self) -> bool:
        """Check if service is available for requests"""
        if self.circuit_open:
            if (
                self.circuit_open_until
                and datetime.now(timezone.utc) > self.circuit_open_until
            ):
                self.circuit_open = False
                self.consecutive_failures = 0
                logger.info(f"Circuit breaker closed for {self.name}")
                return True
            return False

        return self.status in [
            ServiceStatus.HEALTHY,
            ServiceStatus.DEGRADED,
            ServiceStatus.UNKNOWN,
        ]

    def record_success(self, response_time: float) -> None:
        """Record successful request"""
        self.response_time = response_time
        self.error_count = max(0, self.error_count - 1)
        self.consecutive_failures = 0
        if self.circuit_open:
            self.circuit_open = False
            logger.info(
                f"Circuit breaker closed for {self.name} after successful request"
            )

    def record_failure(
        self, circuit_threshold: int = 5, circuit_timeout: int = 60
    ) -> None:
        """Record failed request and manage circuit breaker"""
        self.error_count += 1
        self.consecutive_failures += 1

        if self.consecutive_failures >= circuit_threshold and not self.circuit_open:
            self.circuit_open = True
            self.circuit_open_until = datetime.now(timezone.utc) + timedelta(
                seconds=circuit_timeout
            )
            logger.warning(
                f"Circuit breaker opened for {self.name} after {self.consecutive_failures} failures"
            )


class ServiceRegistry:
    """Service registry with health checking and circuit breaker"""

    def __init__(self, settings: GatewaySettings):
        self.settings = settings
        self.services: Dict[str, ServiceInfo] = {}
        self.http_client = httpx.AsyncClient(timeout=5.0)
        self.health_check_interval = 30  # seconds
        self.health_check_task = None

        # Register services
        self._register_services()

    def _register_services(self):
        """Register all backend services with load balancing support"""
        # Parse user service URLs for load balancing
        user_service_urls = []
        user_service_health_urls = []

        # Check if multiple user service URLs are configured
        if hasattr(self.settings, "USER_SERVICE_URLS"):
            user_service_urls = self.settings.USER_SERVICE_URLS
            user_service_health_urls = getattr(
                self.settings,
                "USER_SERVICE_HEALTH_URLS",
                [f"{url}/health" for url in user_service_urls],
            )
        else:
            # Fallback to single URL
            user_service_urls = [self.settings.USER_SERVICE_URL]
            user_service_health_urls = [self.settings.USER_SERVICE_HEALTH]

        self.services = {
            "user-service": ServiceInfo(
                name="user-service",
                urls=user_service_urls,
                health_urls=user_service_health_urls,
            ),
            "product-service": ServiceInfo(
                name="product-service",
                urls=[self.settings.PRODUCT_SERVICE_URL],
                health_urls=[self.settings.PRODUCT_SERVICE_HEALTH],
            ),
            "order-service": ServiceInfo(
                name="order-service",
                urls=[self.settings.ORDER_SERVICE_URL],
                health_urls=[self.settings.ORDER_SERVICE_HEALTH],
            ),
            "notification_service": ServiceInfo(
                name="notification_service",
                urls=[self.settings.NOTIFICATION_SERVICE_URL],
                health_urls=[self.settings.NOTIFICATION_SERVICE_HEALTH],
            ),
        }

        logger.info(
            f"Registered {len(self.services)} services with load balancing support"
        )

    async def start_health_checks(self):
        """Start periodic health checks"""
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Started service health check loop")

    async def stop_health_checks(self):
        """Stop health checks"""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

        await self.http_client.aclose()
        logger.info("Stopped service health checks")

    async def _health_check_loop(self):
        """Periodic health check loop"""
        while True:
            try:
                await self._check_all_services()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5)  # Short retry delay

    async def _check_all_services(self):
        """Check health of all registered services"""
        tasks = [
            self._check_service_health(service) for service in self.services.values()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_service_health(self, service: ServiceInfo):
        """Check health of all service instances"""
        healthy_count = 0
        total_count = len(service.urls)

        for i, health_url in enumerate(service.health_urls):
            try:
                start_time = asyncio.get_event_loop().time()
                response = await self.http_client.get(health_url)
                response_time = asyncio.get_event_loop().time() - start_time

                if response.status_code == 200:
                    healthy_count += 1
                    # Update response time with the latest healthy response
                    service.response_time = response_time
                else:
                    logger.warning(
                        f"Service {service.name} instance {i + 1} returned status {response.status_code}"
                    )
            except Exception as e:
                logger.error(
                    f"Service {service.name} instance {i + 1} health check failed: {e}"
                )

        # Update service status based on healthy instances
        old_status = service.status
        if healthy_count == total_count:
            service.status = ServiceStatus.HEALTHY
        elif healthy_count > 0:
            service.status = ServiceStatus.DEGRADED
        else:
            service.status = ServiceStatus.UNHEALTHY

        service.last_check = datetime.now(timezone.utc)

        if healthy_count > 0:
            service.record_success(service.response_time or 0)
        else:
            service.record_failure(
                self.settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                self.settings.CIRCUIT_BREAKER_TIMEOUT,
            )

        if old_status != service.status:
            logger.info(
                f"Service {service.name} status changed: {old_status.value} -> {service.status.value} "
                f"({healthy_count}/{total_count} instances healthy)"
            )

    def get_service(self, service_name: str) -> Optional[ServiceInfo]:
        """Get service info by name"""
        return self.services.get(service_name)

    def get_service_url(self, service_name: str) -> Optional[str]:
        """Get next service URL using round-robin load balancing"""
        service = self.get_service(service_name)
        if service and service.is_available():
            return service.get_next_url()
        return None

    def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all services"""
        return {
            name: {
                "status": service.status.value,
                "urls": service.urls,
                "health_urls": service.health_urls,
                "current_url_index": service.current_url_index,
                "last_check": service.last_check.isoformat()
                if service.last_check
                else None,
                "response_time": service.response_time,
                "error_count": service.error_count,
                "circuit_open": service.circuit_open,
            }
            for name, service in self.services.items()
        }
