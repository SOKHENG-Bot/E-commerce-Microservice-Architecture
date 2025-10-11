"""
Product management proxy routes for API Gateway
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from app.routes.proxy import get_service_proxy, ServiceProxy

router = APIRouter(prefix="/products", tags=["products"])


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_product_requests(
    request: Request,
    path: str,
    proxy: ServiceProxy = Depends(get_service_proxy)
):
    """Proxy all product requests to product service"""
    if not proxy:
        raise HTTPException(status_code=503, detail="Service proxy not available")
    
    return await proxy.proxy_request(
        request=request,
        service_name="product-service",
        path=f"/api/v1/products/{path}"
    )


@router.api_route("/", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], include_in_schema=False)
async def proxy_product_root_requests(
    request: Request,
    proxy: ServiceProxy = Depends(get_service_proxy)
):
    """Proxy product root requests to product service"""
    if not proxy:
        raise HTTPException(status_code=503, detail="Service proxy not available")
    
    return await proxy.proxy_request(
        request=request,
        service_name="product-service",
        path="/api/v1/products"
    )


@router.api_route("/categories/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_category_requests(
    request: Request,
    path: str,
    proxy: ServiceProxy = Depends(get_service_proxy)
):
    """Proxy category requests to product service"""
    if not proxy:
        raise HTTPException(status_code=503, detail="Service proxy not available")
    
    return await proxy.proxy_request(
        request=request,
        service_name="product-service",
        path=f"/api/v1/categories/{path}"
    )
