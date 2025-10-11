from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .base import BaseEvent
from .base.kafka_client import KafkaEventPublisher
from .schemas import (
    OrderCreatedEventData,
    OrderStatusUpdatedEventData,
    OrderCancelledEventData,
    OrderShippedEventData,
    OrderDeliveredEventData,
    OrderReturnedEventData,
    OrderRefundedEventData,
)

from ..utils.logging import setup_order_logging as setup_logging

logger = setup_logging("order-producer-events", log_level="INFO")


class BaseEventPublisher:
    """Base class for event publishers with common functionality"""

    def __init__(
        self,
        event_publisher: KafkaEventPublisher,
        source_service: str = "order-service",
    ):
        self.event_publisher = event_publisher
        self.source_service = source_service

    async def _publish_event(
        self,
        event: BaseEvent,
        topic: str,
        event_name: str,
        log_data: Dict[str, Any],
    ) -> None:
        """Common event publishing logic with error handling and logging"""
        try:
            await self.event_publisher.publish(event, topic=topic)
            logger.info(f"Published {event_name} event.", extra=log_data)
        except Exception as e:
            logger.error(f"Failed to publish {event_name} event: {e}")
            raise


class OrderEventPublisher(BaseEventPublisher):
    """Handles order lifecycle events"""

    async def publish_order_created(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        total_amount: Decimal,
        items: List[Dict[str, Any]],
        billing_address: Dict[str, Any],
        shipping_address: Dict[str, Any],
        order_data: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish order created event"""
        # Create event data using schema
        event_data = OrderCreatedEventData(
            order_id=order_id,
            order_number=order_number,
            user_id=user_id,
            total_amount=total_amount,
            items=items,
            billing_address=billing_address,
            shipping_address=shipping_address,
            created_at=datetime.now(timezone.utc),
        )

        # Create BaseEvent
        event = BaseEvent(
            event_type="order.created",
            source_service=self.source_service,
            correlation_id=correlation_id,
            data=event_data.to_dict(),
        )

        # Add additional order data
        if order_data:
            event.data.update(order_data)

        await self._publish_event(
            event=event,
            topic="order.events",
            event_name="order created",
            log_data={
                "order_id": str(order_id),
                "order_number": order_number,
                "user_id": str(user_id),
                "total_amount": str(total_amount),
            },
        )

    async def publish_order_status_updated(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        old_status: str,
        new_status: str,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish order status updated event"""
        # Create event data using schema
        event_data = OrderStatusUpdatedEventData(
            order_id=order_id,
            order_number=order_number,
            user_id=user_id,
            old_status=old_status,
            new_status=new_status,
            updated_at=datetime.now(timezone.utc),
        )

        # Create BaseEvent
        event = BaseEvent(
            event_type="order.status_updated",
            source_service=self.source_service,
            correlation_id=correlation_id,
            data=event_data.to_dict(),
        )

        await self._publish_event(
            event=event,
            topic="order.events",
            event_name="order status updated",
            log_data={
                "order_id": str(order_id),
                "order_number": order_number,
                "old_status": old_status,
                "new_status": new_status,
            },
        )

    async def publish_order_cancelled(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        reason: str,
        refund_amount: Optional[Decimal] = None,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish order cancelled event"""
        # Create event data using schema
        event_data = OrderCancelledEventData(
            order_id=order_id,
            order_number=order_number,
            user_id=user_id,
            reason=reason,
            cancelled_at=datetime.now(timezone.utc),
        )

        # Create BaseEvent
        event = BaseEvent(
            event_type="order.cancelled",
            source_service=self.source_service,
            correlation_id=correlation_id,
            data=event_data.to_dict(),
        )

        # Add refund amount if provided
        if refund_amount is not None:
            event.data["refund_amount"] = str(refund_amount)

        await self._publish_event(
            event=event,
            topic="order.events",
            event_name="order cancelled",
            log_data={
                "order_id": str(order_id),
                "order_number": order_number,
                "reason": reason,
            },
        )

    async def publish_order_shipped(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        tracking_number: Optional[str] = None,
        carrier: Optional[str] = None,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish order shipped event"""
        # Create event data using schema
        event_data = OrderShippedEventData(
            order_id=order_id,
            order_number=order_number,
            user_id=user_id,
            tracking_number=tracking_number,
            carrier=carrier,
            shipped_at=datetime.now(timezone.utc),
        )

        # Create BaseEvent
        event = BaseEvent(
            event_type="order.shipped",
            source_service=self.source_service,
            correlation_id=correlation_id,
            data=event_data.to_dict(),
        )

        await self._publish_event(
            event=event,
            topic="order.events",
            event_name="order shipped",
            log_data={
                "order_id": str(order_id),
                "order_number": order_number,
                "tracking_number": tracking_number,
            },
        )

    async def publish_order_delivered(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        delivered_at: datetime,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish order delivered event"""
        # Create event data using schema
        event_data = OrderDeliveredEventData(
            order_id=order_id,
            order_number=order_number,
            user_id=user_id,
            delivered_at=delivered_at,
        )

        # Create BaseEvent
        event = BaseEvent(
            event_type="order.delivered",
            source_service=self.source_service,
            correlation_id=correlation_id,
            data=event_data.to_dict(),
        )

        await self._publish_event(
            event=event,
            topic="order.events",
            event_name="order delivered",
            log_data={
                "order_id": str(order_id),
                "order_number": order_number,
            },
        )

    async def publish_order_returned(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        reason: Optional[str] = None,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish order returned event"""
        # Create event data using schema
        event_data = OrderReturnedEventData(
            order_id=order_id,
            order_number=order_number,
            user_id=user_id,
            reason=reason,
            returned_at=datetime.now(timezone.utc),
        )

        # Create BaseEvent
        event = BaseEvent(
            event_type="order.returned",
            source_service=self.source_service,
            correlation_id=correlation_id,
            data=event_data.to_dict(),
        )

        await self._publish_event(
            event=event,
            topic="order.events",
            event_name="order returned",
            log_data={
                "order_id": str(order_id),
                "order_number": order_number,
                "reason": reason,
            },
        )

    async def publish_order_refunded(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        refund_amount: Decimal,
        reason: Optional[str] = None,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish order refunded event"""
        # Create event data using schema
        event_data = OrderRefundedEventData(
            order_id=order_id,
            order_number=order_number,
            user_id=user_id,
            refund_amount=refund_amount,
            reason=reason,
            refunded_at=datetime.now(timezone.utc),
        )

        # Create BaseEvent
        event = BaseEvent(
            event_type="order.refunded",
            source_service=self.source_service,
            correlation_id=correlation_id,
            data=event_data.to_dict(),
        )

        await self._publish_event(
            event=event,
            topic="order.events",
            event_name="order refunded",
            log_data={
                "order_id": str(order_id),
                "order_number": order_number,
                "refund_amount": str(refund_amount),
            },
        )


class OrderEventProducer:
    """
    Main order service event producer that combines all event publishers.

    This class provides a unified interface for publishing all types of events
    related to orders.
    """

    def __init__(self, event_publisher: KafkaEventPublisher):
        self.order_publisher = OrderEventPublisher(event_publisher)

    # Order Events
    async def publish_order_created(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        total_amount: Decimal,
        items: List[Dict[str, Any]],
        billing_address: Dict[str, Any],
        shipping_address: Dict[str, Any],
        order_data: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[int] = None,
    ) -> None:
        return await self.order_publisher.publish_order_created(
            order_id,
            order_number,
            user_id,
            total_amount,
            items,
            billing_address,
            shipping_address,
            order_data,
            correlation_id,
        )

    async def publish_order_status_updated(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        old_status: str,
        new_status: str,
        correlation_id: Optional[int] = None,
    ) -> None:
        return await self.order_publisher.publish_order_status_updated(
            order_id, order_number, user_id, old_status, new_status, correlation_id
        )

    async def publish_order_cancelled(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        reason: str,
        refund_amount: Optional[Decimal] = None,
        correlation_id: Optional[int] = None,
    ) -> None:
        return await self.order_publisher.publish_order_cancelled(
            order_id, order_number, user_id, reason, refund_amount, correlation_id
        )

    async def publish_order_shipped(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        tracking_number: Optional[str] = None,
        carrier: Optional[str] = None,
        correlation_id: Optional[int] = None,
    ) -> None:
        return await self.order_publisher.publish_order_shipped(
            order_id, order_number, user_id, tracking_number, carrier, correlation_id
        )

    async def publish_order_delivered(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        delivered_at: datetime,
        correlation_id: Optional[int] = None,
    ) -> None:
        return await self.order_publisher.publish_order_delivered(
            order_id, order_number, user_id, delivered_at, correlation_id
        )

    async def publish_order_returned(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        reason: Optional[str] = None,
        correlation_id: Optional[int] = None,
    ) -> None:
        return await self.order_publisher.publish_order_returned(
            order_id, order_number, user_id, reason, correlation_id
        )

    async def publish_order_refunded(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        refund_amount: Decimal,
        reason: Optional[str] = None,
        correlation_id: Optional[int] = None,
    ) -> None:
        return await self.order_publisher.publish_order_refunded(
            order_id, order_number, user_id, refund_amount, reason, correlation_id
        )
