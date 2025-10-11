"""
Order management proxy routes for API Gateway
"""

from fastapi import APIRouter, Depends, Request

from app.routes.proxy import ServiceProxy, get_service_proxy

router = APIRouter(prefix="/orders", tags=["orders"])


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_order_requests(
    request: Request, path: str, proxy: ServiceProxy = Depends(get_service_proxy)
):
    """Proxy all order requests to order service"""
    return await proxy.proxy_request(
        request=request, service_name="order-service", path=f"/api/v1/orders/{path}"
    )


@router.api_route(
    "/", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], include_in_schema=False
)
async def proxy_order_root_requests(
    request: Request, proxy: ServiceProxy = Depends(get_service_proxy)
):
    """Proxy order root requests to order service"""
    return await proxy.proxy_request(
        request=request, service_name="order-service", path="/api/v1/orders"
    )
