"""
Notification routes for API Gateway
"""

from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.routes.proxy import ServiceProxy, get_service_proxy

router = APIRouter(prefix="/notifications", tags=["notifications"])


async def get_proxy() -> Optional[ServiceProxy]:
    """Get service proxy instance"""
    return get_service_proxy()


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def notification_proxy(
    request: Request, path: str, proxy: Optional[ServiceProxy] = Depends(get_proxy)
) -> Response:
    """
    Forward all notification requests to the notification service
    """
    if not proxy:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Service proxy not available")

    return await proxy.proxy_request(
        request=request,
        service_name="notification_service",
        path=f"/api/v1/notifications/{path}" if path else "/api/v1/notifications",
    )


@router.get("/")
async def list_notifications(
    request: Request, proxy: Optional[ServiceProxy] = Depends(get_proxy)
) -> Response:
    """
    List notifications endpoint
    """
    if not proxy:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Service proxy not available")

    return await proxy.proxy_request(
        request=request,
        service_name="notification_service",
        path="/api/v1/notifications",
    )


@router.post("/send")
async def send_notification(
    request: Request, proxy: Optional[ServiceProxy] = Depends(get_proxy)
) -> Response:
    """
    Send notification endpoint
    """
    if not proxy:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Service proxy not available")

    return await proxy.proxy_request(
        request=request,
        service_name="notification_service",
        path="/api/v1/notifications/send",
    )


@router.get("/user/{user_id}/list")
async def list_user_notifications(
    request: Request, user_id: int, proxy: Optional[ServiceProxy] = Depends(get_proxy)
) -> Response:
    """
    List user notifications endpoint
    """
    if not proxy:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Service proxy not available")

    return await proxy.proxy_request(
        request=request,
        service_name="notification_service",
        path=f"/api/v1/notifications/user/{user_id}/list",
    )


@router.post("/templates")
async def create_template(
    request: Request, proxy: Optional[ServiceProxy] = Depends(get_proxy)
) -> Response:
    """
    Create notification template endpoint
    """
    if not proxy:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Service proxy not available")

    return await proxy.proxy_request(
        request=request, service_name="notification_service", path="/api/v1/templates"
    )


@router.get("/templates")
async def list_templates(
    request: Request, proxy: Optional[ServiceProxy] = Depends(get_proxy)
) -> Response:
    """
    List notification templates endpoint
    """
    if not proxy:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Service proxy not available")

    return await proxy.proxy_request(
        request=request, service_name="notification_service", path="/api/v1/templates"
    )
