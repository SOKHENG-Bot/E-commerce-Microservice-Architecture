from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.deps import DatabaseDep, NotificationServiceDep
from ...schemas.bulk_notification import (
    BulkNotificationCreate,
)
from ...services.bulk_notification_service import BulkNotificationService
from ...utils.logging import setup_notification_logging

logger = setup_notification_logging("bulk_notifications_api")

router = APIRouter(prefix="/bulk-notifications", tags=["bulk-notifications"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def send_bulk_notification(
    request: Request,
    bulk_data: BulkNotificationCreate,
    db: AsyncSession = DatabaseDep,
    notification_service: Any = NotificationServiceDep,
) -> Dict[str, Any]:
    """Send bulk notifications to multiple users."""
    try:
        logger.info(
            "Sending bulk notification",
            extra={
                "total_users": len(bulk_data.user_ids),
                "notification_type": bulk_data.notification_type,
                "channel": bulk_data.channel,
                "batch_size": bulk_data.batch_size,
            },
        )

        # Create bulk notification service
        bulk_service = BulkNotificationService(db, notification_service)

        # Send bulk notification
        result = await bulk_service.send_bulk_notification(
            user_ids=bulk_data.user_ids,
            notification_type=bulk_data.notification_type,
            channel=bulk_data.channel,
            subject=bulk_data.subject,
            content=bulk_data.content,
            template_id=bulk_data.template_id,
            template_data=bulk_data.template_data,
            priority=bulk_data.priority or "medium",
            batch_size=bulk_data.batch_size,
            max_concurrent=bulk_data.max_concurrent,
        )

        logger.info(
            "Bulk notification sent successfully",
            extra={
                "job_id": result["job_id"],
                "total_users": result["total_users"],
                "total_sent": result["total_sent"],
                "success_rate": result["success_rate"],
            },
        )

        return result

    except Exception as e:
        logger.error(f"Failed to send bulk notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send bulk notification",
        )


@router.get("/channels")
async def get_supported_channels(
    request: Request,
) -> Dict[str, List[str]]:
    """Get list of supported notification channels."""
    return {
        "channels": ["email", "sms", "push"],
    }
