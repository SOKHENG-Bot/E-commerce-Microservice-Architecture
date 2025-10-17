from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from jinja2 import Template
from sqlalchemy.ext.asyncio import AsyncSession

from ..events.producers import NotificationEventProducer
from ..providers.email_provider import EmailProvider
from ..providers.push_provider import PushProvider
from ..providers.sms_provider import SMSProvider
from ..repository.notification_repository import NotificationRepository
from ..repository.template_repository import TemplateRepository
from ..schemas.notification import (
    NotificationCreate,
    NotificationPriority,
    NotificationType,
)
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
        self.notification_repository = NotificationRepository(session)
        self.email_provider = EmailProvider()
        self.sms_provider = SMSProvider()
        self.push_provider = PushProvider()

    async def send_email_notification(
        self,
        user_id: int,
        template_name: str,
        template_data: Dict[str, Any],
        correlation_id: Optional[int] = None,
        recipient_email: Optional[str] = None,
        content: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send email notification using database templates with event publishing and delivery tracking
        """
        notification_record = None
        try:
            # Check if using direct content or template
            if content and subject:
                # Direct content mode - no template needed
                rendered_subject = subject
                rendered_body = content
                template = None
                content_type = "text/html"  # Default
            else:
                # Template mode
                template = await self.template_repository.get_by_name(template_name)
                if not template:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Template '{template_name}' not found",
                    )

                # Render templates with Jinja2
                subject_template = Template(template.subject or template_name)
                body_template = Template(template.body)

                rendered_subject = subject_template.render(**template_data)
                rendered_body = body_template.render(**template_data)
                content_type = template.content_type

            notification_id = str(uuid4())

            # Create notification record in database
            if not recipient_email:
                raise ValueError("Recipient email is required for email notifications")

            notification_data = NotificationCreate(
                user_id=user_id,
                type=NotificationType.EMAIL,
                channel="email",
                recipient=recipient_email,
                subject=rendered_subject,
                content=rendered_body,
                template_id=template_name if template else None,
                template_data=template_data if template else None,
                priority=NotificationPriority.MEDIUM,
                max_retries=3,
            )
            notification_record = (
                await self.notification_repository.create_notification(
                    notification_data, user_id
                )
            )

            # Send email using EmailProvider
            try:
                if not recipient_email:
                    raise ValueError(
                        "Recipient email is required for email notifications"
                    )

                email_result = await self.email_provider.send_email(
                    to_email=recipient_email,
                    subject=rendered_subject,
                    content=rendered_body,
                    template_data=None,  # Already rendered
                    is_html=content_type == "text/html",
                )
                success = email_result.get("success", False)
                provider_message_id = email_result.get(
                    "message_id",
                    f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}",
                )
            except Exception as email_error:
                logger.error(f"Email provider error: {email_error}")
                success = False
                provider_message_id = (
                    f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}"
                )

            if success:
                # Update notification as sent
                await self.notification_repository.mark_as_sent(
                    notification_record.id,
                    provider_response={
                        "message_id": provider_message_id,
                        "provider": "sendgrid",
                        "success": True,
                    },
                )

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
                    "content_type": content_type,
                    "rendered_subject": rendered_subject,
                    "rendered_body": rendered_body,
                    "delivered_at": datetime.now(timezone.utc).isoformat(),
                }
            else:
                # Mark notification as failed
                await self.notification_repository.mark_as_failed(
                    notification_record.id,
                    failure_reason="Email delivery failed",
                    increment_retry=False,
                )

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
            # Mark notification as failed if it was created
            if notification_record:
                await self.notification_repository.mark_as_failed(
                    notification_record.id,
                    failure_reason=str(e)[:255],
                    increment_retry=False,
                )

            logger.error(f"Error sending email notification to user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send email notification.",
            )
        finally:
            # Ensure session is committed for successful operations
            try:
                await self.session.commit()
            except Exception as commit_error:
                logger.error(f"Failed to commit session: {commit_error}")
                await self.session.rollback()

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
        notification_record = None
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

            # Create notification record in database
            if not phone_number:
                raise ValueError("Phone number is required for SMS notifications")

            notification_data = NotificationCreate(
                user_id=user_id,
                type=NotificationType.SMS,
                channel="sms",
                recipient=phone_number,
                subject=None,
                content=rendered_message,
                template_id=template_name,
                template_data=template_data,
                priority=NotificationPriority.MEDIUM,
                max_retries=3,
            )
            notification_record = (
                await self.notification_repository.create_notification(
                    notification_data, user_id
                )
            )

            # Send SMS using SMSProvider
            try:
                sms_result = await self.sms_provider.send_sms(
                    to_number=phone_number,
                    content=rendered_message,
                    template_data=template_data,
                )
                success = sms_result.get("success", False)
                message_id = sms_result.get("message_id", message_id)
            except Exception as sms_error:
                logger.error(f"SMS provider error: {sms_error}")
                success = False

            if success:
                # Update notification as sent
                await self.notification_repository.mark_as_sent(
                    notification_record.id,
                    provider_response={
                        "message_id": message_id,
                        "provider": "twilio",  # Assuming Twilio for SMS
                        "success": True,
                    },
                )

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
                # Mark notification as failed
                await self.notification_repository.mark_as_failed(
                    notification_record.id,
                    failure_reason="SMS delivery failed",
                    increment_retry=False,
                )

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to send SMS notification.",
                )

        except Exception as e:
            # Mark notification as failed if it was created
            if notification_record:
                await self.notification_repository.mark_as_failed(
                    notification_record.id, failure_reason=str(e), increment_retry=False
                )

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
        notification_record = None
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

            # Create notification record in database
            if not device_token:
                raise ValueError("Device token is required for push notifications")

            notification_data = NotificationCreate(
                user_id=user_id,
                type=NotificationType.PUSH,
                channel="push",
                recipient=device_token,
                subject=rendered_title,
                content=rendered_message,
                template_id=template_name,
                template_data=template_data,
                priority=NotificationPriority.MEDIUM,
                max_retries=3,
            )
            notification_record = (
                await self.notification_repository.create_notification(
                    notification_data, user_id
                )
            )

            # Send push notification using PushProvider
            try:
                push_result = await self.push_provider.send_push_notification(
                    device_token=device_token,
                    title=rendered_title,
                    body=rendered_message,
                    data=template_data,
                )
                success = push_result.get("success", False)
                notification_id = push_result.get("notification_id", notification_id)
            except Exception as push_error:
                logger.error(f"Push provider error: {push_error}")
                success = False

            if success:
                # Update notification as sent
                await self.notification_repository.mark_as_sent(
                    notification_record.id,
                    provider_response={
                        "notification_id": notification_id,
                        "provider": "fcm",  # Assuming Firebase Cloud Messaging
                        "success": True,
                    },
                )

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
                # Mark notification as failed
                await self.notification_repository.mark_as_failed(
                    notification_record.id,
                    failure_reason="Push notification delivery failed",
                    increment_retry=False,
                )

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to send push notification.",
                )

        except Exception as e:
            # Mark notification as failed if it was created
            if notification_record:
                await self.notification_repository.mark_as_failed(
                    notification_record.id, failure_reason=str(e), increment_retry=False
                )

            logger.error(f"Error sending push notification to user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send push notification.",
            )
