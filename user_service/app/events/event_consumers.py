"""
User Service Event Consumers
===========================

Handles incoming events from other microservices using local event infrastructure.
Processes events to update user statistics, engagement metrics, and cross-service data.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from user_service.app.core.settings import get_settings
from user_service.app.events.base import BaseEvent, EventHandler
from user_service.app.events.base.kafka_client import KafkaEventSubscriber
from user_service.app.repository.user_repository import UserRepository
from user_service.app.utils.logging import setup_user_logging as setup_logging

settings = get_settings()
logger = setup_logging("user_service.events.consumers", log_level=settings.LOG_LEVEL)


class OrderCreatedHandler(EventHandler):
    """Handle order created events using shared event handler interface"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repository = UserRepository(session)

    async def handle(self, event: BaseEvent) -> None:
        """Handle order created event - update user statistics"""
        try:
            # Event data comes from shared OrderCreatedEvent schema
            data = event.data
            user_id = UUID(data["user_id"])
            order_total = float(data["total_amount"])

            # Update user order statistics
            await self._update_user_order_statistics(
                user_id,
                {
                    "new_order": True,
                    "order_amount": order_total,
                    "order_date": data.get("order_date"),
                },
            )

            logger.info(
                "Updated user statistics from order event",
                extra={
                    "user_id": str(user_id),
                    "order_amount": order_total,
                    "correlation_id": str(event.correlation_id)
                    if event.correlation_id
                    else None,
                },
            )

        except Exception as e:
            logger.error(f"Failed to handle order created event: {e}")
            raise

    async def _update_user_order_statistics(
        self, user_id: UUID, order_data: Dict[str, Any]
    ):
        """Update user order statistics"""
        # This would update user statistics in database
        # For now, just log the update
        logger.info(
            "User order statistics updated",
            extra={"user_id": str(user_id), "order_data": order_data},
        )


class NotificationSentHandler(EventHandler):
    """Handle notification sent events to update user engagement metrics"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repository = UserRepository(session)

    async def handle(self, event: BaseEvent) -> None:
        """Handle notification sent event - update user engagement"""
        try:
            data = event.data
            user_id = data["user_id"]  # user_id is an integer, not UUID
            notification_type = data.get("notification_type", "unknown")
            channel = data.get("channel", "email")
            status = data.get("status", "sent")

            # Update user notification preferences and engagement
            await self._update_user_notification_engagement(
                user_id,
                {
                    "notification_type": notification_type,
                    "channel": channel,
                    "status": status,
                    "sent_at": data.get("sent_at"),
                },
            )

            logger.info(
                "Updated user engagement from notification event",
                extra={
                    "user_id": str(user_id),
                    "notification_type": notification_type,
                    "channel": channel,
                    "status": status,
                    "correlation_id": str(event.correlation_id)
                    if event.correlation_id
                    else None,
                },
            )

        except Exception as e:
            logger.error(f"Failed to handle notification sent event: {e}")
            raise

    async def _update_user_notification_engagement(
        self, user_id: int, notification_data: Dict[str, Any]
    ):
        """Update user notification engagement metrics"""
        logger.info(
            "User notification engagement updated",
            extra={"user_id": str(user_id), "notification_data": notification_data},
        )


class PaymentProcessedHandler(EventHandler):
    """Handle payment processed events to update user payment history"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repository = UserRepository(session)

    async def handle(self, event: BaseEvent) -> None:
        """Handle payment processed event - update user payment statistics"""
        try:
            data = event.data
            user_id = UUID(data["user_id"])
            payment_amount = float(data["amount"])
            payment_method = data.get("payment_method", "unknown")
            payment_status = data.get("status", "completed")

            # Update user payment statistics
            await self._update_user_payment_statistics(
                user_id,
                {
                    "payment_amount": payment_amount,
                    "payment_method": payment_method,
                    "payment_status": payment_status,
                    "order_id": data.get("order_id"),
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            logger.info(
                "Updated user payment statistics from payment event",
                extra={
                    "user_id": str(user_id),
                    "payment_amount": payment_amount,
                    "payment_method": payment_method,
                    "payment_status": payment_status,
                    "correlation_id": str(event.correlation_id)
                    if event.correlation_id
                    else None,
                },
            )

        except Exception as e:
            logger.error(f"Failed to handle payment processed event: {e}")
            raise

    async def _update_user_payment_statistics(
        self, user_id: UUID, payment_data: Dict[str, Any]
    ):
        """Update user payment statistics and preferences"""
        logger.info(
            "User payment statistics updated",
            extra={"user_id": str(user_id), "payment_data": payment_data},
        )


class ReviewCreatedHandler(EventHandler):
    """Handle review created events to update user reputation"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repository = UserRepository(session)

    async def handle(self, event: BaseEvent) -> None:
        """Handle review created event - update user reputation score"""
        try:
            data = event.data
            user_id = UUID(data["user_id"])
            rating = int(data.get("rating", 0))
            product_id = data.get("product_id")

            # Update user review statistics
            await self._update_user_review_reputation(
                user_id,
                {
                    "new_review": True,
                    "rating_given": rating,
                    "product_id": product_id,
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            logger.info(
                "Updated user reputation from review event",
                extra={
                    "user_id": str(user_id),
                    "rating": rating,
                    "product_id": product_id,
                    "correlation_id": str(event.correlation_id)
                    if event.correlation_id
                    else None,
                },
            )

        except Exception as e:
            logger.error(f"Failed to handle review created event: {e}")
            raise

    async def _update_user_review_reputation(
        self, user_id: UUID, review_data: Dict[str, Any]
    ):
        """Update user review reputation and engagement"""
        logger.info(
            "User reputation updated",
            extra={"user_id": str(user_id), "review_data": review_data},
        )


class UserActivityHandler(EventHandler):
    """Handle user activity events for analytics and engagement tracking"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repository = UserRepository(session)

    async def handle(self, event: BaseEvent) -> None:
        """Handle user activity event - update user engagement metrics"""
        try:
            data = event.data
            user_id = UUID(data["user_id"])
            activity_type = data.get("activity_type", "unknown")
            session_id = data.get("session_id")

            # Update user activity tracking
            await self._update_user_activity_tracking(
                user_id,
                {
                    "activity_type": activity_type,
                    "session_id": session_id,
                    "page_url": data.get("page_url"),
                    "metadata": data.get("metadata", {}),
                    "tracked_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            logger.info(
                "Updated user activity tracking",
                extra={
                    "user_id": str(user_id),
                    "activity_type": activity_type,
                    "session_id": session_id,
                    "correlation_id": str(event.correlation_id)
                    if event.correlation_id
                    else None,
                },
            )

        except Exception as e:
            logger.error(f"Failed to handle user activity event: {e}")
            raise

    async def _update_user_activity_tracking(
        self, user_id: UUID, activity_data: Dict[str, Any]
    ):
        """Update user activity and engagement metrics"""
        logger.info(
            "User activity metrics updated",
            extra={"user_id": str(user_id), "activity_data": activity_data},
        )


class UserEventConsumer:
    """User service event consumer using shared subscriber"""

    def __init__(self, session: AsyncSession):
        self.session = session
        # Use shared KafkaEventSubscriber
        self.subscriber = KafkaEventSubscriber(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_GROUP_ID,
            client_id="user-service-consumer",
        )

    async def start(self):
        """Start consuming events using shared subscriber"""
        await self.subscriber.start()

        # Register event handlers for different services
        order_handler = OrderCreatedHandler(self.session)
        notification_handler = NotificationSentHandler(self.session)
        payment_handler = PaymentProcessedHandler(self.session)
        review_handler = ReviewCreatedHandler(self.session)
        activity_handler = UserActivityHandler(self.session)

        # Subscribe to multiple event types from different services
        await self.subscriber.subscribe(
            topic="order.events", event_type="order.created", handler=order_handler
        )

        await self.subscriber.subscribe(
            topic="notification.events",
            event_type="notification.sent",
            handler=notification_handler,
        )

        await self.subscriber.subscribe(
            topic="payment.events",
            event_type="payment.processed",
            handler=payment_handler,
        )

        await self.subscriber.subscribe(
            topic="review.events", event_type="review.created", handler=review_handler
        )

        await self.subscriber.subscribe(
            topic="analytics.events",
            event_type="analytics.user_activity",
            handler=activity_handler,
        )

        logger.info(
            "Started consuming user service events",
            extra={
                "subscriptions": [
                    "order.events:order.created",
                    "notification.events:notification.sent",
                    "payment.events:payment.processed",
                    "review.events:review.created",
                    "analytics.events:analytics.user_activity",
                ]
            },
        )

    async def stop(self):
        """Stop event consumer"""
        await self.subscriber.stop()
