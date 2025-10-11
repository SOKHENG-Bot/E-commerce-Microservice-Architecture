"""
Product Service Event Producers
==============================

Handles outgoing events from the product service using shared event infrastructure.
Publishes product, inventory, category, and review-related events to other microservices.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from ..core.setting import get_settings
from ..utils.logging import setup_product_logging as setup_logging
from .base import BaseEvent
from .base.kafka_client import KafkaEventPublisher
from .schemas import (
    CategoryCreatedEventData,
    CategoryUpdatedEventData,
    InventoryUpdatedEventData,
    ProductCreatedEventData,
    ProductUpdatedEventData,
)

settings = get_settings()
logger = setup_logging("product_service.events.producers", log_level=settings.LOG_LEVEL)


class ProductEventProducer:
    """
    Product service event producer using shared event infrastructure.
    Publishes product-related events to other microservices.
    """

    def __init__(self, kafka_publisher: KafkaEventPublisher):
        self.kafka_publisher = kafka_publisher

    # ==============================================
    # PRODUCT EVENTS
    # ==============================================

    async def publish_product_created(
        self,
        product_id: int,
        name: str,
        sku: str,
        price: float,
        category_id: int,
        product_data: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish product created event"""
        try:
            event_data = ProductCreatedEventData(
                product_id=product_id,
                name=name,
                sku=sku,
                price=Decimal(str(price)),
                category_id=category_id,
                description=product_data.get("description") if product_data else None,
                created_at=datetime.now(timezone.utc),
            )

            event = BaseEvent(
                event_type="product.created",
                source_service="product-service",
                data=event_data.to_dict(),
                correlation_id=correlation_id,
            )

            await self.kafka_publisher.publish(event, topic="product.events")
            logger.info(
                "Published product created event",
                extra={
                    "product_id": product_id,
                    "product_name": name,
                    "correlation_id": correlation_id,
                },
            )

        except Exception as e:
            logger.error(f"Failed to publish product created event: {e}")
            raise

    async def publish_product_updated(
        self,
        product_id: int,
        updated_fields: Dict[str, Any],
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish product updated event"""
        try:
            event_data = ProductUpdatedEventData(
                product_id=product_id,
                updated_fields=updated_fields,
                updated_at=datetime.now(timezone.utc),
            )

            event = BaseEvent(
                event_type="product.updated",
                source_service="product-service",
                data=event_data.to_dict(),
                correlation_id=correlation_id,
            )

            await self.kafka_publisher.publish(event, topic="product.events")
            logger.info(
                "Published product updated event",
                extra={
                    "product_id": product_id,
                    "updated_fields": list(updated_fields.keys()),
                    "correlation_id": correlation_id,
                },
            )

        except Exception as e:
            logger.error(f"Failed to publish product updated event: {e}")
            raise

    async def publish_product_deleted(
        self,
        product_id: int,
        product_data: Dict[str, Any],
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish product deleted event"""
        try:
            event = BaseEvent(
                event_type="product.deleted",
                source_service="product-service",
                data={
                    "product_id": product_id,
                    "product_data": product_data,
                    "deleted_at": datetime.now(timezone.utc).isoformat(),
                },
                correlation_id=correlation_id,
            )

            await self.kafka_publisher.publish(event, topic="product.events")
            logger.info(
                "Published product deleted event",
                extra={
                    "product_id": product_id,
                    "correlation_id": correlation_id,
                },
            )

        except Exception as e:
            logger.error(f"Failed to publish product deleted event: {e}")
            raise

    # ==============================================
    # INVENTORY EVENTS
    # ==============================================

    async def publish_inventory_updated(
        self,
        product_id: int,
        variant_id: Optional[int] = None,
        quantity: int = 0,
        reserved_quantity: int = 0,
        previous_quantity: int = 0,
        warehouse_id: Optional[int] = None,
        reason: Optional[str] = None,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish inventory updated event"""
        try:
            event_data = InventoryUpdatedEventData(
                product_id=product_id,
                variant_id=variant_id,
                quantity=quantity,
                reserved_quantity=reserved_quantity,
                previous_quantity=previous_quantity,
                warehouse_id=warehouse_id,
                updated_at=datetime.now(timezone.utc),
                reason=reason,
            )

            event = BaseEvent(
                event_type="inventory.updated",
                source_service="product-service",
                data=event_data.to_dict(),
                correlation_id=correlation_id,
            )

            await self.kafka_publisher.publish(event, topic="inventory.events")
            logger.info(
                "Published inventory updated event",
                extra={
                    "product_id": product_id,
                    "quantity": quantity,
                    "previous_quantity": previous_quantity,
                    "correlation_id": correlation_id,
                },
            )

        except Exception as e:
            logger.error(f"Failed to publish inventory updated event: {e}")
            raise

    # ==============================================
    # CATEGORY EVENTS
    # ==============================================

    async def publish_category_created(
        self,
        category_id: int,
        category_name: str,
        parent_category_id: Optional[int] = None,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish category created event"""
        try:
            event_data = CategoryCreatedEventData(
                category_id=category_id,
                name=category_name,
                parent_id=parent_category_id,
                created_at=datetime.now(timezone.utc),
            )

            event = BaseEvent(
                event_type="category.created",
                source_service="product-service",
                data=event_data.to_dict(),
                correlation_id=correlation_id,
            )

            await self.kafka_publisher.publish(event, topic="category.events")
            logger.info(
                "Published category created event",
                extra={
                    "category_id": category_id,
                    "category_name": category_name,
                    "correlation_id": correlation_id,
                },
            )

        except Exception as e:
            logger.error(f"Failed to publish category created event: {e}")
            raise

    async def publish_category_updated(
        self,
        category_id: int,
        category_name: str,
        updated_fields: Dict[str, Any],
        parent_category_id: Optional[int] = None,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish category updated event"""
        try:
            event_data = CategoryUpdatedEventData(
                category_id=category_id,
                updated_fields=updated_fields,
                updated_at=datetime.now(timezone.utc),
            )

            event = BaseEvent(
                event_type="category.updated",
                source_service="product-service",
                data=event_data.to_dict(),
                correlation_id=correlation_id,
            )

            await self.kafka_publisher.publish(event, topic="category.events")
            logger.info(
                "Published category updated event",
                extra={
                    "category_id": category_id,
                    "updated_fields": list(updated_fields.keys()),
                    "correlation_id": correlation_id,
                },
            )

        except Exception as e:
            logger.error(f"Failed to publish category updated event: {e}")
            raise

    async def publish_category_deleted(
        self,
        category_id: int,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish category deleted event"""
        try:
            event = BaseEvent(
                event_type="category.deleted",
                source_service="product-service",
                data={
                    "category_id": category_id,
                    "deleted_at": datetime.now(timezone.utc).isoformat(),
                },
                correlation_id=correlation_id,
            )

            await self.kafka_publisher.publish(event, topic="category.events")
            logger.info(
                "Published category deleted event",
                extra={
                    "category_id": category_id,
                    "correlation_id": correlation_id,
                },
            )

        except Exception as e:
            logger.error(f"Failed to publish category deleted event: {e}")
            raise
