"""
Notification service with comprehensive notification management and event publishing.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..events.producers import NotificationEventProducer
from ..repository.template_repository import TemplateRepository
from ..utils.logging import setup_notification_logging as setup_logging

logger = setup_logging("notification_service", log_level="INFO")


class NotificationService:
    def __init__(
        self,
        session: AsyncSession,
        event_publisher: Optional[NotificationEventProducer],
    ):
        self.session = session
        self.event_publisher = event_publisher
        self.template_repository = TemplateRepository(session)

    async def send_email_notification(
        self,
        user_id: int,
        template_name: str,
        template_data: Dict[str, Any],
        correlation_id: Optional[int] = None,
        recipient_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send email notification using database templates with event publishing and delivery tracking
        """
        try:
            # Fetch template from database
            template = await self.template_repository.get_by_name(template_name)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Template '{template_name}' not found",
                )

            # Use template content as-is (no variable validation needed)
            rendered_subject = template.subject
            rendered_body = template.body

            notification_id = str(uuid4())

            # Email sending logic here - replace with actual email provider
            success = True  # Mock success - replace with actual email sending
            provider_message_id = (
                f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}"
            )

            if success:
                # Publish notification sent event
                if self.event_publisher:
                    await self.event_publisher.publish_notification_sent(
                        user_id=user_id,
                        notification_type=template_name,
                        channel="email",
                        template_data=template_data,
                        status="sent",
                        correlation_id=correlation_id,
                    )

                logger.info(
                    "Email notification sent successfully.",
                    extra={
                        "user_id": str(user_id),
                        "template_name": template_name,
                        "channel": "email",
                        "notification_id": notification_id,
                        "recipient_email": recipient_email,
                    },
                )

                return {
                    "user_id": user_id,
                    "template_name": template_name,
                    "channel": "email",
                    "status": "delivered",
                    "notification_id": notification_id,
                    "provider_message_id": provider_message_id,
                    "content_type": template.content_type,
                    "rendered_subject": rendered_subject,
                    "rendered_body": rendered_body,
                    "delivered_at": datetime.now(timezone.utc).isoformat(),
                }
            else:
                # Publish notification failed event
                if self.event_publisher:
                    await self.event_publisher.publish_notification_failed(
                        user_id=user_id,
                        notification_type=template_name,
                        channel="email",
                        template_data=template_data,
                        error_reason="Email delivery failed",
                        correlation_id=correlation_id,
                    )

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to send email notification.",
                )

        except Exception as e:
            logger.error(f"Error sending email notification to user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send email notification.",
            )

    async def send_sms_notification(
        self,
        user_id: int,
        template_name: str,
        template_data: Dict[str, Any],
        correlation_id: Optional[int] = None,
        phone_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send SMS notification using database templates with event publishing and delivery tracking
        """
        try:
            # Fetch template from database
            template = await self.template_repository.get_by_name(template_name)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Template '{template_name}' not found",
                )

            # Use template content as-is (no variable validation needed)
            rendered_message = template.body

            notification_id = str(uuid4())
            message_id = f"sms_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}"

            # SMS sending logic here - mock success
            success = True

            if success:
                # Publish SMS delivered event
                if self.event_publisher:
                    await self.event_publisher.publish_sms_delivered(
                        user_id=user_id,
                        phone_number=phone_number or "unknown",
                        message_id=message_id,
                        correlation_id=correlation_id,
                    )

                logger.info(
                    "SMS notification sent successfully.",
                    extra={
                        "user_id": str(user_id),
                        "template_name": template_name,
                        "phone_number": phone_number,
                        "message_id": message_id,
                        "notification_id": notification_id,
                    },
                )

                return {
                    "user_id": user_id,
                    "template_name": template_name,
                    "phone_number": phone_number,
                    "message_id": message_id,
                    "notification_id": notification_id,
                    "rendered_message": rendered_message,
                    "status": "delivered",
                    "delivered_at": datetime.now(timezone.utc).isoformat(),
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to send SMS notification.",
                )

        except Exception as e:
            logger.error(f"Error sending SMS notification to user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send SMS notification.",
            )

    async def send_push_notification(
        self,
        user_id: int,
        template_name: str,
        template_data: Dict[str, Any],
        correlation_id: Optional[int] = None,
        device_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send push notification using database templates with event publishing and delivery tracking
        """
        try:
            # Fetch template from database
            template = await self.template_repository.get_by_name(template_name)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Template '{template_name}' not found",
                )

            # For push notifications, subject becomes title, body becomes message
            rendered_title = template.subject or template_name
            rendered_message = template.body

            notification_id = str(uuid4())

            # Push notification sending logic here - mock success
            success = True

            if success:
                # Publish push notification delivered event
                if self.event_publisher:
                    await self.event_publisher.publish_push_notification_delivered(
                        user_id=user_id,
                        device_token=device_token or "unknown",
                        notification_id=notification_id,
                        title=rendered_title,
                        correlation_id=correlation_id,
                    )

                logger.info(
                    "Push notification sent successfully.",
                    extra={
                        "user_id": str(user_id),
                        "template_name": template_name,
                        "notification_id": notification_id,
                        "title": rendered_title,
                    },
                )

                return {
                    "user_id": user_id,
                    "template_name": template_name,
                    "notification_id": notification_id,
                    "device_token": device_token,
                    "title": rendered_title,
                    "message": rendered_message,
                    "status": "delivered",
                    "delivered_at": datetime.now(timezone.utc).isoformat(),
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to send push notification.",
                )

        except Exception as e:
            logger.error(f"Error sending push notification to user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send push notification.",
            )
