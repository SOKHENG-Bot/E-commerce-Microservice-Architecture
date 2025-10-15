"""
Notification service event producers using local event infrastructure and schemas.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..core.settings import get_settings
from ..utils.logging import setup_notification_logging as setup_logging
from .base import BaseEvent
from .base.kafka_client import KafkaEventPublisher
from .schemas import (
    EmailClickedEventData,
    EmailSentEventData,
    NotificationFailedEventData,
    NotificationPreferencesUpdatedEventData,
    NotificationSentEventData,
    PushNotificationSentEventData,
    SMSSentEventData,
    UserUnsubscribedEventData,
)

settings = get_settings()
logger = setup_logging("notification-producer-events", log_level=settings.LOG_LEVEL)


class NotificationEventProducer:
    """
    Notification service event producer using new BaseEvent pattern with proper schemas.
    All methods now use the corrected event creation pattern.
    """

    def __init__(self, event_publisher: KafkaEventPublisher):
        self.event_publisher = event_publisher

    # ==============================================
    # NOTIFICATION DELIVERY EVENTS
    # ==============================================

    async def publish_notification_sent(
        self,
        user_id: int,
        notification_type: str,
        channel: str,
        template_data: Dict[str, Any],
        status: str = "sent",
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish notification sent event"""
        try:
            # Create event data using schema
            event_data = NotificationSentEventData(
                notification_id=f"notif-{user_id}-{datetime.now(timezone.utc).timestamp()}",
                user_id=str(user_id),
                notification_type=notification_type,
                recipient=template_data.get("recipient", ""),
                subject=template_data.get("subject"),
                content=template_data.get("content", ""),
                metadata={
                    "channel": channel,
                    "status": status,
                    "template_data": template_data,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Create BaseEvent
            event = BaseEvent(
                event_type="notification.sent",
                source_service="notification-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            await self.event_publisher.publish(event, topic="notification.events")
            logger.info(
                "Published notification sent event.",
                extra={
                    "user_id": str(user_id),
                    "type": notification_type,
                    "channel": channel,
                    "status": status,
                },
            )
        except Exception as e:
            logger.error(f"Failed to publish notification sent event: {e}")
            raise

    async def publish_notification_failed(
        self,
        user_id: int,
        notification_type: str,
        channel: str,
        template_data: Dict[str, Any],
        error_reason: str,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish notification failed event"""
        try:
            # Create event data using schema
            event_data = NotificationFailedEventData(
                notification_id=f"notif-{user_id}-{datetime.now(timezone.utc).timestamp()}",
                user_id=str(user_id),
                notification_type=notification_type,
                recipient=template_data.get("recipient", ""),
                error_message=error_reason,
                retry_count=0,
                metadata={
                    "channel": channel,
                    "template_data": template_data,
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Create BaseEvent
            event = BaseEvent(
                event_type="notification.failed",
                source_service="notification-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            await self.event_publisher.publish(event, topic="notification.events")
            logger.info(
                "Published notification failed event.",
                extra={
                    "user_id": str(user_id),
                    "type": notification_type,
                    "channel": channel,
                    "error": error_reason,
                },
            )
        except Exception as e:
            logger.error(f"Failed to publish notification failed event: {e}")
            raise

    # ==============================================
    # EMAIL TRACKING EVENTS
    # ==============================================

    async def publish_email_opened(
        self,
        user_id: int,
        notification_id: str,
        email_subject: str,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish email opened event"""
        try:
            # Create event data using schema
            event_data = EmailSentEventData(
                notification_id=notification_id,
                user_id=str(user_id),
                recipient="",  # Would need to be passed in or looked up
                subject=email_subject,
                content="",  # Content not needed for opened event
                metadata={
                    "opened_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Create BaseEvent
            event = BaseEvent(
                event_type="email.opened",
                source_service="notification-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            await self.event_publisher.publish(event, topic="notification.events")
            logger.info(
                "Published email opened event.",
                extra={
                    "user_id": str(user_id),
                    "notification_id": notification_id,
                },
            )
        except Exception as e:
            logger.error(f"Failed to publish email opened event: {e}")
            raise

    async def publish_email_clicked(
        self,
        user_id: int,
        notification_id: str,
        link_url: str,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish email clicked event"""
        try:
            # Create event data using schema
            event_data = EmailClickedEventData(
                notification_id=notification_id,
                user_id=str(user_id),
                link_url=link_url,
                clicked_at=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "clicked_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Create BaseEvent
            event = BaseEvent(
                event_type="email.clicked",
                source_service="notification-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            await self.event_publisher.publish(event, topic="notification.events")
            logger.info(
                "Published email clicked event.",
                extra={
                    "user_id": str(user_id),
                    "notification_id": notification_id,
                    "link": link_url,
                },
            )
        except Exception as e:
            logger.error(f"Failed to publish email clicked event: {e}")
            raise

    # ==============================================
    # SMS TRACKING EVENTS
    # ==============================================

    async def publish_sms_delivered(
        self,
        user_id: int,
        phone_number: str,
        message_id: str,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish SMS delivered event"""
        try:
            # Create event data using schema
            event_data = SMSSentEventData(
                notification_id=f"sms-{user_id}-{datetime.now(timezone.utc).timestamp()}",
                user_id=str(user_id),
                recipient=phone_number,
                content="",  # Content not needed for delivered event
                provider="unknown",  # Would need to be passed in
                message_id=message_id,
                metadata={
                    "delivered_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Create BaseEvent
            event = BaseEvent(
                event_type="sms.delivered",
                source_service="notification-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            await self.event_publisher.publish(event, topic="notification.events")
            logger.info(
                "Published SMS delivered event.",
                extra={
                    "user_id": str(user_id),
                    "message_id": message_id,
                    "phone": phone_number,
                },
            )
        except Exception as e:
            logger.error(f"Failed to publish SMS delivered event: {e}")
            raise

    # ==============================================
    # PUSH NOTIFICATION EVENTS
    # ==============================================

    async def publish_push_notification_delivered(
        self,
        user_id: int,
        device_token: str,
        notification_id: str,
        title: str,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish push notification delivered event"""
        try:
            # Create event data using schema
            event_data = PushNotificationSentEventData(
                notification_id=notification_id,
                user_id=str(user_id),
                device_token=device_token,
                title=title,
                body="",  # Body not needed for delivered event
                metadata={
                    "delivered_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Create BaseEvent
            event = BaseEvent(
                event_type="push.delivered",
                source_service="notification-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            await self.event_publisher.publish(event, topic="notification.events")
            logger.info(
                "Published push notification delivered event.",
                extra={
                    "user_id": str(user_id),
                    "notification_id": notification_id,
                    "title": title,
                },
            )
        except Exception as e:
            logger.error(f"Failed to publish push notification delivered event: {e}")
            raise

    # ==============================================
    # NOTIFICATION PREFERENCES EVENTS
    # ==============================================

    async def publish_notification_preferences_updated(
        self,
        user_id: int,
        preferences: Dict[str, Any],
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish notification preferences updated event"""
        try:
            # Create event data using schema
            event_data = NotificationPreferencesUpdatedEventData(
                user_id=str(user_id),
                preferences=preferences,
                updated_at=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Create BaseEvent
            event = BaseEvent(
                event_type="notification.preferences_updated",
                source_service="notification-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            await self.event_publisher.publish(event, topic="notification.events")
            logger.info(
                "Published notification preferences updated event.",
                extra={
                    "user_id": str(user_id),
                    "preferences": list(preferences.keys()),
                },
            )
        except Exception as e:
            logger.error(
                f"Failed to publish notification preferences updated event: {e}"
            )
            raise

    async def publish_user_unsubscribed(
        self,
        user_id: int,
        notification_type: str,
        channel: str,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish user unsubscribed event"""
        try:
            # Create event data using schema
            event_data = UserUnsubscribedEventData(
                user_id=str(user_id),
                notification_type=notification_type,
                channel=channel,
                unsubscribed_at=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "unsubscribed_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Create BaseEvent
            event = BaseEvent(
                event_type="notification.unsubscribed",
                source_service="notification-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            await self.event_publisher.publish(event, topic="notification.events")
            logger.info(
                "Published user unsubscribed event.",
                extra={
                    "user_id": str(user_id),
                    "type": notification_type,
                    "channel": channel,
                },
            )
        except Exception as e:
            logger.error(f"Failed to publish user unsubscribed event: {e}")
            raise
