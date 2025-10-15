import logging
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.events import get_event_producer
from ..core.settings import get_settings
from ..services.notification_service import NotificationService
from .base import BaseEvent, EventHandler
from .base.kafka_client import KafkaEventSubscriber

settings = get_settings()
logger = logging.getLogger(__name__)


class EmailVerificationHandler(EventHandler):
    """Handle email verification request events to send verification emails"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.event_producer = get_event_producer()
        self.notification_service = NotificationService(session, self.event_producer)

    async def handle(self, event: BaseEvent) -> None:
        """Handle email verification request event - send verification email"""
        try:
            data = event.data
            user_id = data["user_id"]
            email = data["email"]
            verification_token = data["verification_token"]
            expires_in_minutes = data["expires_in_minutes"]

            # Create verification link
            verification_url = f"http://localhost:8010/api/v1/auth/verify-email-token/{verification_token}"

            # Send email verification notification
            template_data: Dict[str, Any] = {
                "user_email": email,
                "verification_url": verification_url,
                "expires_in_minutes": expires_in_minutes,
            }

            await self.notification_service.send_email_notification(
                user_id=user_id,
                template_name="email_verification",
                template_data=template_data,
                recipient_email=email,
            )

            logger.info(
                "Sent email verification notification",
                extra={
                    "user_id": str(user_id),
                    "email": email,
                    "correlation_id": str(event.correlation_id)
                    if event.correlation_id
                    else None,
                },
            )
        except Exception as e:
            logger.error(f"Failed to handle email verification request event: {e}")
            raise


class UserCreatedHandler(EventHandler):
    """Handle user created events to send welcome notifications"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.event_producer = get_event_producer()
        self.notification_service = NotificationService(session, self.event_producer)

    async def handle(self, event: BaseEvent) -> None:
        """Handle user created event - send welcome notification"""
        try:
            data = event.data
            user_id = data["user_id"]
            email = data["email"]
            first_name = data.get("first_name")

            # Send welcome email notification
            template_data: Dict[str, Any] = {
                "user_name": first_name or "there",
                "user_email": email,
            }

            await self.notification_service.send_email_notification(
                user_id=user_id,
                template_name="welcome_email",
                template_data=template_data,
                recipient_email=email,
            )

            logger.info(
                "Sent welcome notification for new user",
                extra={
                    "user_id": str(user_id),
                    "email": email,
                    "correlation_id": str(event.correlation_id)
                    if event.correlation_id
                    else None,
                },
            )
        except Exception as e:
            logger.error(f"Failed to handle user created event: {e}")
            raise


class OrderCreatedHandler(EventHandler):
    """Handle order created events to send order confirmation notifications"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.event_producer = get_event_producer()
        self.notification_service = NotificationService(session, self.event_producer)

    async def handle(self, event: BaseEvent) -> None:
        """Handle order created event - send order confirmation"""
        try:
            data = event.data
            user_id = data["user_id"]
            order_id = data["order_id"]
            total_amount = data["total_amount"]
            customer_email = data.get("customer_email")

            # Send order confirmation notification
            template_data: Dict[str, Any] = {
                "order_id": str(order_id),
                "total_amount": str(total_amount),
                "customer_name": customer_email or "Valued Customer",
            }

            await self.notification_service.send_email_notification(
                user_id=user_id,
                template_name="order_confirmation",
                template_data=template_data,
                recipient_email=customer_email,
            )

            logger.info(
                "Sent order confirmation notification",
                extra={
                    "user_id": str(user_id),
                    "order_id": str(order_id),
                    "amount": total_amount,
                    "correlation_id": str(event.correlation_id)
                    if event.correlation_id
                    else None,
                },
            )
        except Exception as e:
            logger.error(f"Failed to handle order created event: {e}")
            raise


class OrderShippedHandler(EventHandler):
    """Handle order shipped events to send shipping notifications"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.event_producer = get_event_producer()
        self.notification_service = NotificationService(session, self.event_producer)

    async def handle(self, event: BaseEvent) -> None:
        """Handle order shipped event - send shipping notification"""
        try:
            data = event.data
            user_id = data["user_id"]
            order_id = data["order_id"]
            tracking_number = data.get("tracking_number")
            carrier = data.get("carrier")
            customer_email = data.get("customer_email")

            # Send order shipped notification
            template_data: Dict[str, Any] = {
                "order_id": str(order_id),
                "tracking_number": tracking_number or "TBD",
                "carrier": carrier or "Our Shipping Partner",
                "customer_name": customer_email or "Valued Customer",
            }

            await self.notification_service.send_email_notification(
                user_id=user_id,
                template_name="order_shipped",
                template_data=template_data,
                recipient_email=customer_email,
            )

            logger.info(
                "Sent order shipped notification",
                extra={
                    "user_id": str(user_id),
                    "order_id": str(order_id),
                    "tracking": tracking_number,
                    "correlation_id": str(event.correlation_id)
                    if event.correlation_id
                    else None,
                },
            )
        except Exception as e:
            logger.error(f"Failed to handle order shipped event: {e}")
            raise


class NotificationEventConsumer:
    """Notification service event consumer using local subscriber"""

    def __init__(self, session: AsyncSession):
        self.session = session
        # Use local KafkaEventSubscriber with faster failure
        self.subscriber = KafkaEventSubscriber(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_GROUP_ID,
            client_id="notification-service-consumer",
            max_retries=3,  # Reduced from 5 to 3
            retry_delay=1.0,  # Reduced from 2.0 to 1.0
            enable_graceful_degradation=True,
        )

    async def start(self):
        """Start consuming events using local subscriber"""
        await self.subscriber.start()

        # Register event handlers for different services
        email_verification_handler = EmailVerificationHandler(self.session)
        user_created_handler = UserCreatedHandler(self.session)
        order_created_handler = OrderCreatedHandler(self.session)
        order_shipped_handler = OrderShippedHandler(self.session)

        # Subscribe to multiple event types from different services
        await self.subscriber.subscribe(
            topic="user.events",
            event_type="user.email_verification_requested",
            handler=email_verification_handler,
        )

        await self.subscriber.subscribe(
            topic="user.events", event_type="user.created", handler=user_created_handler
        )

        await self.subscriber.subscribe(
            topic="order.events",
            event_type="order.created",
            handler=order_created_handler,
        )

        await self.subscriber.subscribe(
            topic="order.events",
            event_type="order.shipped",
            handler=order_shipped_handler,
        )

        logger.info(
            "Started consuming notification service events",
            extra={
                "subscriptions": [
                    "user.events:user.email_verification_requested",
                    "user.events:user.created",
                    "order.events:order.created",
                    "order.events:order.shipped",
                ]
            },
        )

    async def stop(self):
        """Stop event consumer"""
        await self.subscriber.stop()
