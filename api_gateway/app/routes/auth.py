"""
Authentication proxy routes for API Gateway
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.routes.proxy import ServiceProxy, get_service_proxy

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_auth_requests(
    request: Request, path: str, proxy: ServiceProxy = Depends(get_service_proxy)
):
    """Proxy all authentication requests to user service"""
    if not proxy:
        raise HTTPException(status_code=503, detail="Service proxy not available")

    return await proxy.proxy_request(
        request=request, service_name="user-service", path=f"/api/v1/auth/{path}"
    )
