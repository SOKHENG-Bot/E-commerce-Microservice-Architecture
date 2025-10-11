"""
Order service event consumers for handling events from other services.
Focuses on payment processing, product updates, and order lifecycle management.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.setting import get_settings
from ..events.producers import OrderEventProducer
from ..utils.logging import setup_order_logging as setup_logging
from .base import BaseEvent, EventHandler
from .base.kafka_client import KafkaEventSubscriber

settings = get_settings()
logger = setup_logging("order-consumer-events", log_level="INFO")


class PaymentProcessedHandler(EventHandler):
    """Handle payment processed events to update order status"""

    def __init__(self, session: AsyncSession, event_producer: OrderEventProducer):
        self.session = session
        self.event_producer = event_producer

    async def handle(self, event: BaseEvent) -> None:
        """Handle payment processed event - update order status to paid"""
        try:
            data = event.data
            payment_id = data["payment_id"]
            order_id = data["order_id"]
            amount = data["amount"]
            status = data["status"]
            correlation_id = str(event.correlation_id) if event.correlation_id else None

            logger.info(
                f"Processing payment processed event for order {order_id}",
                extra={
                    "payment_id": payment_id,
                    "order_id": order_id,
                    "amount": str(amount),
                    "status": status,
                    "correlation_id": correlation_id,
                },
            )

            # For now, just log the payment processing
            # In a real implementation, this would update the payment record in the database
            logger.info(
                f"Payment processed for order {order_id}: status={status}",
                extra={
                    "payment_id": payment_id,
                    "order_id": order_id,
                    "amount": str(amount),
                    "status": status,
                    "correlation_id": correlation_id,
                },
            )

            # Mock order status update - in real implementation would call order service
            if status == "completed":
                logger.info(
                    f"Order {order_id} would be marked as paid",
                    extra={
                        "order_id": order_id,
                        "payment_id": payment_id,
                        "correlation_id": correlation_id,
                    },
                )

        except Exception as e:
            logger.error(
                f"Failed to process payment processed event: {e}", exc_info=True
            )
            raise


class PaymentFailedHandler(EventHandler):
    """Handle payment failed events to update order and payment status"""

    def __init__(self, session: AsyncSession, event_producer: OrderEventProducer):
        self.session = session
        self.event_producer = event_producer

    async def handle(self, event: BaseEvent) -> None:
        """Handle payment failed event - update order status and handle failure"""
        try:
            data = event.data
            payment_id = data["payment_id"]
            order_id = data["order_id"]
            error_reason = data.get("error_reason", "Unknown payment failure")
            correlation_id = str(event.correlation_id) if event.correlation_id else None

            logger.info(
                f"Processing payment failed event for order {order_id}",
                extra={
                    "payment_id": payment_id,
                    "order_id": order_id,
                    "error_reason": error_reason,
                    "correlation_id": correlation_id,
                },
            )

            # For now, just log the payment failure
            # In a real implementation, this would update the payment record in the database
            logger.warning(
                f"Payment failed for order {order_id}: {error_reason}",
                extra={
                    "payment_id": payment_id,
                    "order_id": order_id,
                    "error_reason": error_reason,
                    "correlation_id": correlation_id,
                },
            )

            # Mock order status update - in real implementation would call order service
            logger.info(
                f"Order {order_id} would be marked as payment_failed",
                extra={
                    "order_id": order_id,
                    "payment_id": payment_id,
                    "correlation_id": correlation_id,
                },
            )

        except Exception as e:
            logger.error(f"Failed to process payment failed event: {e}", exc_info=True)
            raise


class RefundProcessedHandler(EventHandler):
    """Handle refund processed events to update order and payment records"""

    def __init__(self, session: AsyncSession, event_producer: OrderEventProducer):
        self.session = session
        self.event_producer = event_producer

    async def handle(self, event: BaseEvent) -> None:
        """Handle refund processed event - record refund and update order"""
        try:
            data = event.data
            refund_id = data["refund_id"]
            payment_id = data["payment_id"]
            order_id = data["order_id"]
            refund_amount = data["refund_amount"]
            reason = data.get("reason", "Customer refund")
            correlation_id = str(event.correlation_id) if event.correlation_id else None

            logger.info(
                f"Processing refund processed event for order {order_id}",
                extra={
                    "refund_id": refund_id,
                    "payment_id": payment_id,
                    "order_id": order_id,
                    "refund_amount": str(refund_amount),
                    "reason": reason,
                    "correlation_id": correlation_id,
                },
            )

            # For now, just log the refund processing
            # In a real implementation, this would record the refund in the database
            logger.info(
                f"Refund processed for order {order_id}: amount={refund_amount}, reason={reason}",
                extra={
                    "refund_id": refund_id,
                    "payment_id": payment_id,
                    "order_id": order_id,
                    "refund_amount": str(refund_amount),
                    "reason": reason,
                    "correlation_id": correlation_id,
                },
            )

            # Mock order status update for full refunds
            # In real implementation would check if this is a full refund and update order status
            logger.info(
                f"Refund recorded for order {order_id}",
                extra={
                    "refund_id": refund_id,
                    "order_id": order_id,
                    "refund_amount": str(refund_amount),
                    "correlation_id": correlation_id,
                },
            )

        except Exception as e:
            logger.error(
                f"Failed to process refund processed event: {e}", exc_info=True
            )
            raise


class ProductUpdatedHandler(EventHandler):
    """Handle product updated events to update order item information"""

    def __init__(self, session: AsyncSession, event_producer: OrderEventProducer):
        self.session = session
        self.event_producer = event_producer

    async def handle(self, event: BaseEvent) -> None:
        """Handle product updated event - update order items if necessary"""
        try:
            data = event.data
            product_id = data["product_id"]
            correlation_id = str(event.correlation_id) if event.correlation_id else None

            logger.info(
                f"Processing product updated event for product {product_id}",
                extra={
                    "product_id": product_id,
                    "correlation_id": correlation_id,
                },
            )

            # Check if any pending orders contain this product and need updates
            # This would typically involve checking for price changes, name changes, etc.
            # For now, just log the event for potential future processing
            logger.info(
                f"Product {product_id} updated - checking for affected orders",
                extra={
                    "product_id": product_id,
                    "changes": data.get("changes", {}),
                    "correlation_id": correlation_id,
                },
            )

        except Exception as e:
            logger.error(f"Failed to process product updated event: {e}", exc_info=True)
            # Don't raise for product updates - they're not critical for order processing


class ProductDeletedHandler(EventHandler):
    """Handle product deleted events to flag affected orders"""

    def __init__(self, session: AsyncSession, event_producer: OrderEventProducer):
        self.session = session
        self.event_producer = event_producer

    async def handle(self, event: BaseEvent) -> None:
        """Handle product deleted event - flag orders containing deleted products"""
        try:
            data = event.data
            product_id = data["product_id"]
            correlation_id = str(event.correlation_id) if event.correlation_id else None

            logger.warning(
                f"Processing product deleted event for product {product_id}",
                extra={
                    "product_id": product_id,
                    "correlation_id": correlation_id,
                },
            )

            # For now, just log the product deletion
            # In a real implementation, this would query and flag affected orders
            logger.warning(
                f"Product {product_id} deleted - would check for affected orders",
                extra={
                    "product_id": product_id,
                    "correlation_id": correlation_id,
                },
            )

        except Exception as e:
            logger.error(f"Failed to process product deleted event: {e}", exc_info=True)
            # Don't raise for product deletions - log and continue


class InventoryLowStockHandler(EventHandler):
    """Handle low stock alerts to notify about potential fulfillment issues"""

    def __init__(self, session: AsyncSession, event_producer: OrderEventProducer):
        self.session = session
        self.event_producer = event_producer

    async def handle(self, event: BaseEvent) -> None:
        """Handle low stock event - check for affected pending orders"""
        try:
            data = event.data
            product_id = data["product_id"]
            available_quantity = data.get("available_quantity", 0)
            correlation_id = str(event.correlation_id) if event.correlation_id else None

            logger.info(
                f"Processing low stock alert for product {product_id}",
                extra={
                    "product_id": product_id,
                    "available_quantity": available_quantity,
                    "correlation_id": correlation_id,
                },
            )

            # For now, just log the low stock alert
            # In a real implementation, this would query pending orders and flag issues
            logger.info(
                f"Low stock alert for product {product_id}: {available_quantity} available",
                extra={
                    "product_id": product_id,
                    "available_quantity": available_quantity,
                    "correlation_id": correlation_id,
                },
            )

        except Exception as e:
            logger.error(f"Failed to process low stock alert: {e}", exc_info=True)
            # Don't raise for stock alerts - they're informational


class InventoryOutOfStockHandler(EventHandler):
    """Handle out of stock events to cancel or flag affected orders"""

    def __init__(self, session: AsyncSession, event_producer: OrderEventProducer):
        self.session = session
        self.event_producer = event_producer

    async def handle(self, event: BaseEvent) -> None:
        """Handle out of stock event - cancel affected orders or flag issues"""
        try:
            data = event.data
            product_id = data["product_id"]
            correlation_id = str(event.correlation_id) if event.correlation_id else None

            logger.warning(
                f"Processing out of stock event for product {product_id}",
                extra={
                    "product_id": product_id,
                    "correlation_id": correlation_id,
                },
            )

            # For now, just log the out of stock event
            # In a real implementation, this would query and cancel affected orders
            logger.warning(
                f"Product {product_id} is out of stock - would cancel affected orders",
                extra={
                    "product_id": product_id,
                    "correlation_id": correlation_id,
                },
            )

        except Exception as e:
            logger.error(f"Failed to process out of stock event: {e}", exc_info=True)
            raise


class OrderEventConsumer:
    """Order service event consumer using local subscriber"""

    def __init__(self, session: AsyncSession, event_producer: OrderEventProducer):
        self.session = session
        self.event_producer = event_producer
        self.subscriber = KafkaEventSubscriber(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id="order-service-consumers",
            client_id="order-service-consumer",
        )

    async def start(self):
        """Start consuming events using local subscriber"""
        await self.subscriber.start()

        # Create event handlers
        payment_processed_handler = PaymentProcessedHandler(
            self.session, self.event_producer
        )
        payment_failed_handler = PaymentFailedHandler(self.session, self.event_producer)
        refund_processed_handler = RefundProcessedHandler(
            self.session, self.event_producer
        )
        product_updated_handler = ProductUpdatedHandler(
            self.session, self.event_producer
        )
        product_deleted_handler = ProductDeletedHandler(
            self.session, self.event_producer
        )
        low_stock_handler = InventoryLowStockHandler(self.session, self.event_producer)
        out_of_stock_handler = InventoryOutOfStockHandler(
            self.session, self.event_producer
        )

        # Subscribe to payment events (CRITICAL PRIORITY)
        await self.subscriber.subscribe(
            topic="payment.events",
            event_type="payment.processed",
            handler=payment_processed_handler,
        )

        await self.subscriber.subscribe(
            topic="payment.events",
            event_type="payment.failed",
            handler=payment_failed_handler,
        )

        await self.subscriber.subscribe(
            topic="payment.events",
            event_type="refund.processed",
            handler=refund_processed_handler,
        )

        # Subscribe to product events (HIGH PRIORITY)
        await self.subscriber.subscribe(
            topic="product.events",
            event_type="product.updated",
            handler=product_updated_handler,
        )

        await self.subscriber.subscribe(
            topic="product.events",
            event_type="product.deleted",
            handler=product_deleted_handler,
        )

        # Subscribe to inventory events (HIGH PRIORITY)
        await self.subscriber.subscribe(
            topic="inventory.events",
            event_type="inventory.low_stock",
            handler=low_stock_handler,
        )

        await self.subscriber.subscribe(
            topic="inventory.events",
            event_type="inventory.out_of_stock",
            handler=out_of_stock_handler,
        )

        logger.info(
            "Started consuming order service events",
            extra={
                "subscriptions": [
                    "payment.events:payment.processed",
                    "payment.events:payment.failed",
                    "payment.events:refund.processed",
                    "product.events:product.updated",
                    "product.events:product.deleted",
                    "inventory.events:inventory.low_stock",
                    "inventory.events:inventory.out_of_stock",
                ]
            },
        )

    async def stop(self):
        """Stop consuming events"""
        await self.subscriber.stop()
        logger.info("Stopped order service event consumer")


# Consumer instance management
_consumer_instance: Optional[OrderEventConsumer] = None


async def get_order_event_consumer(
    session: AsyncSession, event_producer: OrderEventProducer
) -> OrderEventConsumer:
    """Get or create the order event consumer instance"""
    global _consumer_instance

    if _consumer_instance is None:
        _consumer_instance = OrderEventConsumer(session, event_producer)
        await _consumer_instance.start()

    return _consumer_instance


async def shutdown_order_event_consumer():
    """Shutdown the order event consumer"""
    global _consumer_instance

    if _consumer_instance is not None:
        await _consumer_instance.stop()
        _consumer_instance = None
