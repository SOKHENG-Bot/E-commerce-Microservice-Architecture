"""Inventory service for business logic"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..events.event_producers import ProductEventProducer
from ..repository.inventory_repository import InventoryRepository
from ..schemas.inventory import (
    InventoryAdjustment,
    InventoryCreate,
    InventoryResponse,
    InventoryUpdate,
)
from ..utils.logging import setup_product_logging as setup_logging

# Setup structured logging for the service
logger = setup_logging("inventory_service")


class InventoryService:
    """Service class for inventory business logic"""

    def __init__(
        self, db: AsyncSession, event_producer: Optional[ProductEventProducer] = None
    ):
        self.db = db
        self.repository = InventoryRepository(db)
        self.event_producer = event_producer

    async def create_inventory(
        self,
        inventory_data: InventoryCreate,
        user_id: str,
        correlation_id: Optional[str] = None,
    ) -> InventoryResponse:
        """Create new inventory record"""
        try:
            inventory = await self.repository.create_inventory(inventory_data)

            logger.info(
                "Inventory created successfully",
                extra={
                    "inventory_id": inventory.id,
                    "product_id": inventory.product_id,
                    "quantity": inventory.quantity,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                },
            )

            return InventoryResponse(
                id=inventory.id,
                product_id=inventory.product_id,
                variant_id=inventory.variant_id,
                quantity=inventory.quantity,
                reserved_quantity=inventory.reserved_quantity,
                reorder_level=inventory.reorder_level,
                warehouse_location=inventory.warehouse_location,
                created_at=inventory.created_at,
                updated_at=inventory.updated_at,
            )

        except Exception as e:
            logger.error(
                f"Failed to create inventory: {str(e)}",
                extra={
                    "product_id": inventory_data.product_id,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def get_inventory_by_product(
        self, product_id: int, correlation_id: Optional[str] = None
    ) -> Optional[InventoryResponse]:
        """Get inventory by product ID"""
        inventory = await self.repository.get_inventory_by_product(product_id)
        if not inventory:
            return None

        logger.info(
            "Inventory retrieved",
            extra={
                "product_id": product_id,
                "inventory_id": inventory.id,
                "correlation_id": correlation_id,
            },
        )

        return InventoryResponse(
            id=inventory.id,
            product_id=inventory.product_id,
            variant_id=inventory.variant_id,
            quantity=inventory.quantity,
            reserved_quantity=inventory.reserved_quantity,
            reorder_level=inventory.reorder_level,
            warehouse_location=inventory.warehouse_location,
            created_at=inventory.created_at,
            updated_at=inventory.updated_at,
        )

    async def get_inventory_by_id(
        self, inventory_id: int, correlation_id: Optional[str] = None
    ) -> Optional[InventoryResponse]:
        """Get inventory by ID"""
        inventory = await self.repository.get_inventory_by_id(inventory_id)
        if not inventory:
            return None

        logger.info(
            "Inventory retrieved by ID",
            extra={
                "inventory_id": inventory_id,
                "correlation_id": correlation_id,
            },
        )

        return InventoryResponse(
            id=inventory.id,
            product_id=inventory.product_id,
            variant_id=inventory.variant_id,
            quantity=inventory.quantity,
            reserved_quantity=inventory.reserved_quantity,
            reorder_level=inventory.reorder_level,
            warehouse_location=inventory.warehouse_location,
            created_at=inventory.created_at,
            updated_at=inventory.updated_at,
        )

    async def update_inventory(
        self,
        inventory_id: int,
        inventory_data: InventoryUpdate,
        user_id: str,
        correlation_id: Optional[str] = None,
    ) -> Optional[InventoryResponse]:
        """Update inventory"""
        try:
            # Get current inventory for comparison
            current_inventory = await self.repository.get_inventory_by_id(inventory_id)
            if not current_inventory:
                return None

            previous_quantity = current_inventory.quantity

            inventory = await self.repository.update_inventory(
                inventory_id, inventory_data
            )
            if not inventory:
                return None

            logger.info(
                "Inventory updated successfully",
                extra={
                    "inventory_id": inventory_id,
                    "previous_quantity": previous_quantity,
                    "new_quantity": inventory.quantity,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                },
            )

            # Publish inventory updated event
            if self.event_producer:
                await self.event_producer.publish_inventory_updated(
                    product_id=inventory.product_id,
                    variant_id=inventory.variant_id,
                    quantity=inventory.quantity,
                    reserved_quantity=inventory.reserved_quantity,
                    previous_quantity=previous_quantity,
                    warehouse_id=None,  # Not tracked in current schema
                    reason="manual_update",
                    correlation_id=int(correlation_id) if correlation_id else None,
                )

            return InventoryResponse(
                id=inventory.id,
                product_id=inventory.product_id,
                variant_id=inventory.variant_id,
                quantity=inventory.quantity,
                reserved_quantity=inventory.reserved_quantity,
                reorder_level=inventory.reorder_level,
                warehouse_location=inventory.warehouse_location,
                created_at=inventory.created_at,
                updated_at=inventory.updated_at,
            )

        except Exception as e:
            logger.error(
                f"Failed to update inventory: {str(e)}",
                extra={
                    "inventory_id": inventory_id,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def adjust_quantity(
        self,
        inventory_id: int,
        adjustment: InventoryAdjustment,
        user_id: str,
        correlation_id: Optional[str] = None,
    ) -> Optional[InventoryResponse]:
        """Adjust inventory quantity"""
        try:
            # Get current inventory
            current_inventory = await self.repository.get_inventory_by_id(inventory_id)
            if not current_inventory:
                return None

            previous_quantity = current_inventory.quantity

            inventory = await self.repository.adjust_quantity(
                inventory_id, adjustment.quantity_change, adjustment.reason
            )
            if not inventory:
                return None

            logger.info(
                "Inventory adjusted successfully",
                extra={
                    "inventory_id": inventory_id,
                    "previous_quantity": previous_quantity,
                    "quantity_change": adjustment.quantity_change,
                    "new_quantity": inventory.quantity,
                    "reason": adjustment.reason,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                },
            )

            # Publish inventory updated event
            if self.event_producer:
                await self.event_producer.publish_inventory_updated(
                    product_id=inventory.product_id,
                    variant_id=inventory.variant_id,
                    quantity=inventory.quantity,
                    reserved_quantity=inventory.reserved_quantity,
                    previous_quantity=previous_quantity,
                    warehouse_id=None,  # Not tracked in current schema
                    reason=adjustment.reason or "adjustment",
                    correlation_id=int(correlation_id) if correlation_id else None,
                )

            return InventoryResponse(
                id=inventory.id,
                product_id=inventory.product_id,
                variant_id=inventory.variant_id,
                quantity=inventory.quantity,
                reserved_quantity=inventory.reserved_quantity,
                reorder_level=inventory.reorder_level,
                warehouse_location=inventory.warehouse_location,
                created_at=inventory.created_at,
                updated_at=inventory.updated_at,
            )

        except Exception as e:
            logger.error(
                f"Failed to adjust inventory: {str(e)}",
                extra={
                    "inventory_id": inventory_id,
                    "quantity_change": adjustment.quantity_change,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def reserve_quantity(
        self,
        inventory_id: int,
        quantity: int,
        user_id: str,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Reserve quantity for orders"""
        try:
            success = await self.repository.reserve_quantity(inventory_id, quantity)
            if success:
                logger.info(
                    "Quantity reserved successfully",
                    extra={
                        "inventory_id": inventory_id,
                        "reserved_quantity": quantity,
                        "user_id": user_id,
                        "correlation_id": correlation_id,
                    },
                )

                # Publish inventory updated event for reservation
                if self.event_producer:
                    # Get updated inventory to get current state
                    inventory = await self.repository.get_inventory_by_id(inventory_id)
                    if inventory:
                        await self.event_producer.publish_inventory_updated(
                            product_id=inventory.product_id,
                            variant_id=inventory.variant_id,
                            quantity=inventory.quantity,
                            reserved_quantity=inventory.reserved_quantity,
                            previous_quantity=inventory.quantity
                            + quantity,  # Before reservation
                            warehouse_id=None,
                            reason="reservation",
                            correlation_id=int(correlation_id)
                            if correlation_id
                            else None,
                        )

            return success

        except Exception as e:
            logger.error(
                f"Failed to reserve quantity: {str(e)}",
                extra={
                    "inventory_id": inventory_id,
                    "quantity": quantity,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def fulfill_reservation(
        self,
        inventory_id: int,
        quantity: int,
        user_id: str,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Fulfill reservation by reducing both reserved and total quantity"""
        try:
            success = await self.repository.fulfill_reservation(inventory_id, quantity)
            if success:
                logger.info(
                    "Reservation fulfilled successfully",
                    extra={
                        "inventory_id": inventory_id,
                        "fulfilled_quantity": quantity,
                        "user_id": user_id,
                        "correlation_id": correlation_id,
                    },
                )

                # Publish inventory updated event for fulfillment
                if self.event_producer:
                    # Get updated inventory to get current state
                    inventory = await self.repository.get_inventory_by_id(inventory_id)
                    if inventory:
                        await self.event_producer.publish_inventory_updated(
                            product_id=inventory.product_id,
                            variant_id=inventory.variant_id,
                            quantity=inventory.quantity,
                            reserved_quantity=inventory.reserved_quantity,
                            previous_quantity=inventory.quantity
                            + quantity,  # Before fulfillment
                            warehouse_id=None,
                            reason="fulfillment",
                            correlation_id=int(correlation_id)
                            if correlation_id
                            else None,
                        )

            return success

        except Exception as e:
            logger.error(
                f"Failed to fulfill reservation: {str(e)}",
                extra={
                    "inventory_id": inventory_id,
                    "quantity": quantity,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def get_inventory_by_variant(
        self, variant_id: int, correlation_id: Optional[str] = None
    ) -> Optional[InventoryResponse]:
        """Get inventory by variant ID"""
        inventory = await self.repository.get_inventory_by_variant(variant_id)
        if not inventory:
            return None

        logger.info(
            "Inventory retrieved by variant",
            extra={
                "variant_id": variant_id,
                "inventory_id": inventory.id,
                "correlation_id": correlation_id,
            },
        )

        return InventoryResponse(
            id=inventory.id,
            product_id=inventory.product_id,
            variant_id=inventory.variant_id,
            quantity=inventory.quantity,
            reserved_quantity=inventory.reserved_quantity,
            reorder_level=inventory.reorder_level,
            warehouse_location=inventory.warehouse_location,
            created_at=inventory.created_at,
            updated_at=inventory.updated_at,
        )

    async def release_reservation(
        self,
        inventory_id: int,
        quantity: int,
        user_id: str,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Release reserved quantity"""
        try:
            success = await self.repository.release_reservation(inventory_id, quantity)
            if success:
                logger.info(
                    "Reservation released successfully",
                    extra={
                        "inventory_id": inventory_id,
                        "released_quantity": quantity,
                        "user_id": user_id,
                        "correlation_id": correlation_id,
                    },
                )

                # Publish inventory updated event for release
                if self.event_producer:
                    # Get updated inventory to get current state
                    inventory = await self.repository.get_inventory_by_id(inventory_id)
                    if inventory:
                        await self.event_producer.publish_inventory_updated(
                            product_id=inventory.product_id,
                            variant_id=inventory.variant_id,
                            quantity=inventory.quantity,
                            reserved_quantity=inventory.reserved_quantity,
                            previous_quantity=inventory.quantity
                            - quantity,  # Before release
                            warehouse_id=None,
                            reason="release",
                            correlation_id=int(correlation_id)
                            if correlation_id
                            else None,
                        )

            return success

        except Exception as e:
            logger.error(
                f"Failed to release reservation: {str(e)}",
                extra={
                    "inventory_id": inventory_id,
                    "quantity": quantity,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def get_available_quantity(
        self, inventory_id: int, correlation_id: Optional[str] = None
    ) -> int:
        """Get available quantity (total - reserved)"""
        try:
            available_quantity = await self.repository.get_available_quantity(
                inventory_id
            )

            logger.info(
                "Available quantity retrieved",
                extra={
                    "inventory_id": inventory_id,
                    "available_quantity": available_quantity,
                    "correlation_id": correlation_id,
                },
            )

            return available_quantity

        except Exception as e:
            logger.error(
                f"Failed to get available quantity: {str(e)}",
                extra={
                    "inventory_id": inventory_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def delete_inventory(
        self, inventory_id: int, user_id: str, correlation_id: Optional[str] = None
    ) -> bool:
        """Delete inventory record"""
        try:
            success = await self.repository.delete_inventory(inventory_id)
            if success:
                logger.info(
                    "Inventory deleted successfully",
                    extra={
                        "inventory_id": inventory_id,
                        "user_id": user_id,
                        "correlation_id": correlation_id,
                    },
                )

            return success

        except Exception as e:
            logger.error(
                f"Failed to delete inventory: {str(e)}",
                extra={
                    "inventory_id": inventory_id,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise
