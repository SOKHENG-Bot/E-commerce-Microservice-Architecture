"""
User management proxy routes for API Gateway
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from app.routes.proxy import get_service_proxy, ServiceProxy

router = APIRouter(prefix="/users", tags=["users"])


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_user_requests(
    request: Request,
    path: str,
    proxy: ServiceProxy = Depends(get_service_proxy)
):
    """Proxy all user requests to user service"""
    if not proxy:
        raise HTTPException(status_code=503, detail="Service proxy not available")
    
    return await proxy.proxy_request(
        request=request,
        service_name="user-service", 
        path=f"/api/v1/users/{path}"
    )


@router.api_route("/", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], include_in_schema=False)
async def proxy_user_root_requests(
    request: Request,
    proxy: ServiceProxy = Depends(get_service_proxy)
):
    """Proxy user root requests to user service"""
    if not proxy:
        raise HTTPException(status_code=503, detail="Service proxy not available")
    
    return await proxy.proxy_request(
        request=request,
        service_name="user-service",
        path="/api/v1/users"
    )
