"""
Product Service Event Consumers
==============================

Handles incoming events from other microservices using local event infrastructure.
Processes events to update product inventory, handle orders, and manage product analytics.
"""

from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.setting import get_settings
from ..services.inventory_service import InventoryService
from ..utils.logging import setup_product_logging as setup_logging
from .base import BaseEvent, EventHandler
from .base.kafka_client import KafkaEventSubscriber
from .event_producers import ProductEventProducer

settings = get_settings()
logger = setup_logging("product_service.events.consumers", log_level=settings.LOG_LEVEL)


class OrderCreatedHandler(EventHandler):
    """Handle order created events to reserve inventory for ordered items"""

    def __init__(self, session: AsyncSession, event_producer: ProductEventProducer):
        self.session = session
        self.event_producer = event_producer
        self.inventory_service = InventoryService(session)

    async def handle(self, event: BaseEvent) -> None:
        """Handle order created event - reserve inventory for all ordered items"""
        try:
            data = event.data
            order_id = data["order_id"]
            order_items = data.get("items", [])
            correlation_id = str(event.correlation_id) if event.correlation_id else None

            logger.info(
                "Processing inventory reservation for order",
                extra={
                    "order_id": order_id,
                    "items_count": len(order_items),
                    "correlation_id": correlation_id,
                },
            )

            async with self.session as session:
                for item in order_items:
                    product_id = int(item["product_id"])
                    quantity = int(item["quantity"])

                    try:
                        # Get inventory record first
                        inventory = (
                            await self.inventory_service.get_inventory_by_product(
                                product_id=product_id,
                                correlation_id=correlation_id,
                            )
                        )

                        if inventory and inventory.quantity >= quantity:
                            # Reserve inventory using existing method
                            success = await self.inventory_service.reserve_quantity(
                                inventory_id=inventory.id,
                                quantity=quantity,
                                user_id="system",
                                correlation_id=correlation_id,
                            )

                            if success:
                                logger.info(
                                    "Reserved inventory for product",
                                    extra={
                                        "product_id": product_id,
                                        "quantity": quantity,
                                        "order_id": order_id,
                                        "correlation_id": correlation_id,
                                    },
                                )
                            else:
                                logger.warning(
                                    "Failed to reserve inventory for product",
                                    extra={
                                        "product_id": product_id,
                                        "quantity": quantity,
                                        "order_id": order_id,
                                        "correlation_id": correlation_id,
                                    },
                                )
                        else:
                            logger.warning(
                                "Insufficient inventory for product",
                                extra={
                                    "product_id": product_id,
                                    "requested_quantity": quantity,
                                    "available_quantity": inventory.quantity
                                    if inventory
                                    else 0,
                                    "order_id": order_id,
                                    "correlation_id": correlation_id,
                                },
                            )

                    except Exception as item_error:
                        logger.error(
                            "Error processing inventory for product",
                            extra={
                                "product_id": product_id,
                                "quantity": quantity,
                                "order_id": order_id,
                                "error": str(item_error),
                                "correlation_id": correlation_id,
                            },
                            exc_info=True,
                        )

        except Exception as e:
            logger.error(f"Failed to process order created event: {e}")
            raise


class OrderFulfilledHandler(EventHandler):
    """Handle order fulfilled events to permanently deduct inventory"""

    def __init__(self, session: AsyncSession, event_producer: ProductEventProducer):
        self.session = session
        self.event_producer = event_producer
        self.inventory_service = InventoryService(session)

    async def handle(self, event: BaseEvent) -> None:
        """Handle order fulfilled event - permanently deduct inventory"""
        try:
            data = event.data
            order_id = data["order_id"]
            order_items = data.get("items", [])
            correlation_id = str(event.correlation_id) if event.correlation_id else None

            logger.info(
                "Processing inventory fulfillment for order",
                extra={
                    "order_id": order_id,
                    "items_count": len(order_items),
                    "correlation_id": correlation_id,
                },
            )

            async with self.session as session:
                for item in order_items:
                    product_id = int(item["product_id"])
                    quantity = int(item["quantity"])

                    try:
                        # Get inventory record
                        inventory = (
                            await self.inventory_service.get_inventory_by_product(
                                product_id=product_id,
                                correlation_id=correlation_id,
                            )
                        )

                        if inventory:
                            previous_quantity = inventory.quantity

                            # Fulfill the reservation (deduct from both reserved and total)
                            success = await self.inventory_service.fulfill_reservation(
                                inventory_id=inventory.id,
                                quantity=quantity,
                                user_id="system",
                                correlation_id=correlation_id,
                            )

                            if success:
                                # Publish inventory updated event
                                await self.event_producer.publish_inventory_updated(
                                    product_id=product_id,
                                    variant_id=inventory.variant_id,
                                    quantity=previous_quantity - quantity,
                                    reserved_quantity=inventory.reserved_quantity
                                    - quantity,
                                    previous_quantity=previous_quantity,
                                    correlation_id=event.correlation_id,
                                )

                                logger.info(
                                    "Fulfilled inventory for product",
                                    extra={
                                        "product_id": product_id,
                                        "quantity_fulfilled": quantity,
                                        "previous_quantity": previous_quantity,
                                        "order_id": order_id,
                                        "correlation_id": correlation_id,
                                    },
                                )
                            else:
                                logger.error(
                                    "Failed to fulfill reservation for product",
                                    extra={
                                        "product_id": product_id,
                                        "quantity": quantity,
                                        "order_id": order_id,
                                        "correlation_id": correlation_id,
                                    },
                                )

                    except Exception as item_error:
                        logger.error(
                            "Error fulfilling inventory for product",
                            extra={
                                "product_id": product_id,
                                "quantity": quantity,
                                "order_id": order_id,
                                "error": str(item_error),
                                "correlation_id": correlation_id,
                            },
                            exc_info=True,
                        )

        except Exception as e:
            logger.error(f"Failed to handle order fulfilled event: {e}", exc_info=True)
            raise


class BulkOperationHandler(EventHandler):
    """Handle bulk operation events for system monitoring and analytics"""

    def __init__(self, session: AsyncSession, event_producer: ProductEventProducer):
        self.session = session
        self.event_producer = event_producer

    async def handle(self, event: BaseEvent) -> None:
        """Handle bulk operation completion events"""
        try:
            data = event.data
            operation_id = data.get("operation_id", "unknown")
            event_type = event.event_type
            correlation_id = str(event.correlation_id) if event.correlation_id else None

            logger.info(
                "Processing bulk operation event",
                extra={
                    "operation_id": operation_id,
                    "event_type": event_type,
                    "correlation_id": correlation_id,
                    "success_count": data.get("success_count", 0),
                    "failed_count": data.get("failed_count", 0),
                },
            )

            # Handle different types of bulk operations
            if event_type == "bulk_products_imported":
                await self._handle_bulk_import(data, correlation_id)
            elif event_type == "bulk_inventory_updated":
                await self._handle_bulk_inventory_update(data, correlation_id)
            elif event_type == "bulk_prices_updated":
                await self._handle_bulk_price_update(data, correlation_id)
            elif event_type == "products_exported":
                await self._handle_product_export(data, correlation_id)

        except Exception as e:
            logger.error(f"Failed to process bulk operation event: {e}")
            raise

    async def _handle_bulk_import(
        self, data: Dict[str, Any], correlation_id: str = None
    ) -> None:
        """Handle bulk product import completion"""
        success_count = data.get("success_count", 0)
        failed_count = data.get("failed_count", 0)

        logger.info(
            "Bulk import completed",
            extra={
                "success_count": success_count,
                "failed_count": failed_count,
                "success_rate": data.get("success_rate", 0),
                "correlation_id": correlation_id,
            },
        )

    async def _handle_bulk_inventory_update(
        self, data: Dict[str, Any], correlation_id: str = None
    ) -> None:
        """Handle bulk inventory update completion"""
        success_count = data.get("success_count", 0)
        total_quantity_changed = data.get("total_quantity_changed", 0)

        logger.info(
            "Bulk inventory update completed",
            extra={
                "success_count": success_count,
                "total_quantity_changed": total_quantity_changed,
                "update_type": data.get("update_type", "unknown"),
                "correlation_id": correlation_id,
            },
        )

    async def _handle_bulk_price_update(
        self, data: Dict[str, Any], correlation_id: str = None
    ) -> None:
        """Handle bulk price update completion"""
        success_count = data.get("success_count", 0)
        price_change_type = data.get("price_change_type", "unknown")

        logger.info(
            "Bulk price update completed",
            extra={
                "success_count": success_count,
                "price_change_type": price_change_type,
                "average_change": data.get("average_price_change"),
                "correlation_id": correlation_id,
            },
        )

    async def _handle_product_export(
        self, data: Dict[str, Any], correlation_id: str = None
    ) -> None:
        """Handle product export completion"""
        product_count = data.get("product_count", 0)
        export_format = data.get("export_format", "unknown")

        logger.info(
            "Product export completed",
            extra={
                "product_count": product_count,
                "export_format": export_format,
                "file_path": data.get("file_path"),
                "correlation_id": correlation_id,
            },
        )


class ProductEventConsumer:
    """Product service event consumer using shared subscriber"""

    def __init__(self, session: AsyncSession, event_producer: ProductEventProducer):
        self.session = session
        self.event_producer = event_producer
        # Use shared KafkaEventSubscriber
        self.subscriber = KafkaEventSubscriber(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_GROUP_ID,
            client_id=f"{settings.SERVICE_NAME}-consumer",
        )

    async def start(self):
        """Start consuming events using shared subscriber"""
        await self.subscriber.start()

        # Register event handlers for different services
        order_created_handler = OrderCreatedHandler(self.session, self.event_producer)
        order_fulfilled_handler = OrderFulfilledHandler(
            self.session, self.event_producer
        )
        bulk_operation_handler = BulkOperationHandler(self.session, self.event_producer)

        # Subscribe to critical order events (HIGH PRIORITY)
        await self.subscriber.subscribe(
            topic="order.events",
            event_type="order.created",
            handler=order_created_handler,
        )

        await self.subscriber.subscribe(
            topic="order.events",
            event_type="order.fulfilled",
            handler=order_fulfilled_handler,
        )

        # Subscribe to bulk operation events (HIGH PRIORITY for monitoring)
        await self.subscriber.subscribe(
            topic="product.events",
            event_type="bulk_products_imported",
            handler=bulk_operation_handler,
        )

        await self.subscriber.subscribe(
            topic="inventory.events",
            event_type="bulk_inventory_updated",
            handler=bulk_operation_handler,
        )

        await self.subscriber.subscribe(
            topic="product.events",
            event_type="bulk_prices_updated",
            handler=bulk_operation_handler,
        )

        await self.subscriber.subscribe(
            topic="product.events",
            event_type="products_exported",
            handler=bulk_operation_handler,
        )

        logger.info(
            "Started consuming product service events",
            extra={
                "subscriptions": [
                    "order.events:order.created",
                    "order.events:order.fulfilled",
                    "product.events:bulk_products_imported",
                    "inventory.events:bulk_inventory_updated",
                    "product.events:bulk_prices_updated",
                    "product.events:products_exported",
                ]
            },
        )

    async def stop(self):
        """Stop event consumer"""
        await self.subscriber.stop()
