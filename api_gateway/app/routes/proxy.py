"""
Service proxy routes for API Gateway
"""

import time
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Request, Response, status

from app.config.settings import GatewaySettings
from app.core.service_registry import ServiceRegistry

# Import independent logging
from ..utils.logging import setup_api_gateway_logging

logger = setup_api_gateway_logging("api_gateway_proxy")

router = APIRouter()


class ServiceProxy:
    """HTTP proxy to backend services with circuit breaker"""

    def __init__(self, settings: GatewaySettings, service_registry: ServiceRegistry):
        self.settings = settings
        self.service_registry = service_registry
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.settings.REQUEST_TIMEOUT),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )

    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()

    async def proxy_request(
        self,
        request: Request,
        service_name: str,
        path: str,
        preserve_host: bool = False,
    ) -> Response:
        """Proxy request to backend service"""
        service_url = self.service_registry.get_service_url(service_name)

        if not service_url:
            service = self.service_registry.get_service(service_name)
            if service and service.circuit_open:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Service {service_name} is temporarily unavailable (circuit breaker open)",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Service {service_name} is not available",
                )

        # Build target URL
        target_url = f"{service_url}{path}"
        if request.url.query:
            target_url = f"{target_url}?{request.url.query}"

        # Prepare headers
        headers = dict(request.headers)

        # Remove hop-by-hop headers
        hop_by_hop = {
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailers",
            "transfer-encoding",
            "upgrade",
        }
        headers = {k: v for k, v in headers.items() if k.lower() not in hop_by_hop}

        # Add correlation ID for request tracing
        correlation_id = (
            request.headers.get("X-Correlation-ID") or f"gw-{int(time.time() * 1000)}"
        )
        headers["X-Correlation-ID"] = correlation_id

        # Add user context if available
        if hasattr(request.state, "user_id"):
            headers["X-User-ID"] = request.state.user_id

        # Get request body
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()

        try:
            start_time = time.time()

            # Make request to backend service
            backend_response = await self.http_client.request(
                method=request.method, url=target_url, headers=headers, content=body
            )

            response_time = time.time() - start_time

            # Record successful request
            service = self.service_registry.get_service(service_name)
            if service:
                service.record_success(response_time)

            # Log successful proxy request
            logger.info(
                "Proxied request successfully",
                extra={
                    "service": service_name,
                    "method": request.method,
                    "path": path,
                    "status_code": backend_response.status_code,
                    "response_time": response_time,
                    "correlation_id": correlation_id,
                },
            )

            # Prepare response headers
            response_headers = dict(backend_response.headers)

            # Remove hop-by-hop headers from response
            response_headers = {
                k: v for k, v in response_headers.items() if k.lower() not in hop_by_hop
            }

            # Add gateway headers
            response_headers["X-Gateway-Service"] = service_name
            response_headers["X-Response-Time"] = str(round(response_time * 1000, 2))
            response_headers["X-Correlation-ID"] = correlation_id

            # Return response
            return Response(
                content=backend_response.content,
                status_code=backend_response.status_code,
                headers=response_headers,
                media_type=backend_response.headers.get("content-type"),
            )

        except httpx.TimeoutException as e:
            # Record service failure
            service = self.service_registry.get_service(service_name)
            if service:
                service.record_failure(
                    self.settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                    self.settings.CIRCUIT_BREAKER_TIMEOUT,
                )

            logger.error(
                "Service request timeout",
                extra={
                    "service": service_name,
                    "method": request.method,
                    "path": path,
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
            )

            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Service {service_name} request timeout",
            )

        except httpx.ConnectError as e:
            # Record service failure
            service = self.service_registry.get_service(service_name)
            if service:
                service.record_failure(
                    self.settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                    self.settings.CIRCUIT_BREAKER_TIMEOUT,
                )

            logger.error(
                "Service connection error",
                extra={
                    "service": service_name,
                    "method": request.method,
                    "path": path,
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
            )

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Cannot connect to service {service_name}",
            )

        except Exception as e:
            # Record service failure
            service = self.service_registry.get_service(service_name)
            if service:
                service.record_failure(
                    self.settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                    self.settings.CIRCUIT_BREAKER_TIMEOUT,
                )

            logger.error(
                "Service request error",
                extra={
                    "service": service_name,
                    "method": request.method,
                    "path": path,
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
            )

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error communicating with service {service_name}",
            )


# Initialize proxy
service_proxy = None


def set_service_proxy(proxy: ServiceProxy) -> None:
    """Set the service proxy instance"""
    global service_proxy
    service_proxy = proxy


def get_service_proxy() -> Optional[ServiceProxy]:
    """Get service proxy instance"""
    global service_proxy
    return service_proxy
