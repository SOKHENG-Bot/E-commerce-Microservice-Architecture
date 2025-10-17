from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.deps import (
    DatabaseDep,
    NotificationServiceDep,
)
from ...repository.notification_repository import NotificationRepository
from ...schemas.notification import NotificationCreate, NotificationResponse
from ...services.notification_service import NotificationService
from ...utils.logging import setup_notification_logging

# Setup enhanced logging
logger = setup_notification_logging("notifications_api")

router = APIRouter(tags=["Notifications"])


@router.post("/send", status_code=status.HTTP_201_CREATED)
async def send_notification(
    request: Request,
    notification_data: NotificationCreate,
    user_id: int = Query(..., description="User ID"),
    correlation_id: Optional[str] = None,
    notification_service: NotificationService = NotificationServiceDep,
) -> Dict[str, Any]:
    """Send a notification using the NotificationService"""
    try:
        logger.info(
            "Sending notification",
            extra={
                "correlation_id": correlation_id,
                "user_id": str(user_id),
                "notification_type": notification_data.type.value,
            },
        )

        # Send notification using NotificationService (which now handles database persistence)
        notification_success = False
        result = {}

        try:
            # Use NotificationService based on notification type
            if notification_data.type.value == "email":
                result = await notification_service.send_email_notification(
                    user_id=user_id,
                    template_name="custom",  # Use a generic template name
                    template_data=notification_data.template_data or {},
                    correlation_id=int(correlation_id) if correlation_id else None,
                    recipient_email=notification_data.recipient,
                    content=notification_data.content,
                    subject=notification_data.subject,
                )
                notification_success = result.get("status") == "delivered"

            elif notification_data.type.value == "sms":
                result = await notification_service.send_sms_notification(
                    user_id=user_id,
                    template_name="custom",  # Use a generic template name
                    template_data=notification_data.template_data or {},
                    correlation_id=int(correlation_id) if correlation_id else None,
                    phone_number=notification_data.recipient,
                )
                notification_success = result.get("status") == "delivered"

            elif notification_data.type.value == "push":
                result = await notification_service.send_push_notification(
                    user_id=user_id,
                    template_name="custom",  # Use a generic template name
                    template_data=notification_data.template_data or {},
                    correlation_id=int(correlation_id) if correlation_id else None,
                    device_token=notification_data.recipient,
                )
                notification_success = result.get("status") == "delivered"

        except Exception as e:
            logger.error(f"Notification service error: {e}")
            notification_success = False

        response_data: Dict[str, Any] = {
            "notification_id": result.get("notification_id", "unknown"),
            "status": "sent" if notification_success else "failed",
            "message": "Notification sent successfully"
            if notification_success
            else "Notification failed to send",
        }

        logger.info(
            "Notification API call completed",
            extra={
                "correlation_id": correlation_id,
                "notification_id": result.get("notification_id", "unknown"),
                "status": "sent" if notification_success else "failed",
            },
        )

        return response_data

    except Exception as e:
        logger.error(
            f"Failed to send notification: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}",
        )


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    request: Request,
    notification_id: int,
    correlation_id: Optional[str] = None,
    session: AsyncSession = DatabaseDep,
):
    """Get a specific notification"""
    try:
        logger.info(
            f"Retrieving notification {notification_id}",
            extra={
                "correlation_id": correlation_id,
                "notification_id": str(notification_id),
            },
        )

        repository = NotificationRepository(session)

        notification = await repository.get_notification(notification_id)
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
            )

        logger.info(
            f"Notification {notification_id} retrieved successfully",
            extra={
                "correlation_id": correlation_id,
                "notification_id": str(notification_id),
                "status": notification.status,
            },
        )

        return notification

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to retrieve notification {notification_id}: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve notification: {str(e)}",
        )


@router.get("/user/{user_id}/list")
async def list_user_notifications(
    user_id: int,
    skip: int = Query(0, ge=0, description="Number of notifications to skip"),
    limit: int = Query(
        50, ge=1, le=100, description="Number of notifications to return"
    ),
    notification_status: Optional[str] = Query(
        None, description="Filter by status", alias="status"
    ),
    notification_type: Optional[str] = Query(None, description="Filter by type"),
    correlation_id: Optional[str] = None,
    session: AsyncSession = DatabaseDep,
) -> Dict[str, Any]:
    """Get user's notifications with pagination and filters"""
    try:
        repository = NotificationRepository(session)

        notifications, total = await repository.get_notifications_by_user(
            user_id=user_id,
            skip=skip,
            limit=limit,
            status=notification_status,
            notification_type=notification_type,
        )

        return {
            "notifications": notifications,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve notifications: {str(e)}",
        )
