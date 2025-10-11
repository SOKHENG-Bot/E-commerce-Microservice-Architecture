"""Inventory repository for database operations"""

from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.inventory import Inventory
from ..schemas.inventory import InventoryCreate, InventoryUpdate


class InventoryRepository:
    """Repository for inventory database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_inventory(self, inventory_data: InventoryCreate) -> Inventory:
        """Create a new inventory record"""
        inventory = Inventory(
            product_id=inventory_data.product_id,
            variant_id=inventory_data.variant_id,
            quantity=inventory_data.quantity,
            reserved_quantity=inventory_data.reserved_quantity or 0,
            reorder_level=inventory_data.reorder_level,
            warehouse_location=inventory_data.warehouse_location,
        )

        self.db.add(inventory)
        await self.db.commit()
        await self.db.refresh(inventory)
        return inventory

    async def get_inventory_by_id(self, inventory_id: int) -> Optional[Inventory]:
        """Get inventory by ID"""
        query = select(Inventory).where(Inventory.id == inventory_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_inventory_by_product(self, product_id: int) -> Optional[Inventory]:
        """Get inventory by product ID"""
        query = select(Inventory).where(
            and_(Inventory.product_id == product_id, Inventory.variant_id.is_(None))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_inventory_by_variant(self, variant_id: int) -> Optional[Inventory]:
        """Get inventory by variant ID"""
        query = select(Inventory).where(Inventory.variant_id == variant_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_inventory(
        self, inventory_id: int, inventory_data: InventoryUpdate
    ) -> Optional[Inventory]:
        """Update inventory"""
        inventory = await self.get_inventory_by_id(inventory_id)
        if not inventory:
            return None

        update_data = inventory_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(inventory, field, value)

        await self.db.commit()
        await self.db.refresh(inventory)
        return inventory

    async def adjust_quantity(
        self, inventory_id: int, quantity_change: int, reason: str = "manual_adjustment"
    ) -> Optional[Inventory]:
        """Adjust inventory quantity (positive or negative)"""
        inventory = await self.get_inventory_by_id(inventory_id)
        if not inventory:
            return None

        # Ensure quantity doesn't go negative
        new_quantity = max(0, inventory.quantity + quantity_change)
        inventory.quantity = new_quantity

        await self.db.commit()
        await self.db.refresh(inventory)
        return inventory

    async def reserve_quantity(self, inventory_id: int, quantity: int) -> bool:
        """Reserve quantity for orders"""
        inventory = await self.get_inventory_by_id(inventory_id)
        if not inventory:
            return False

        available_quantity = inventory.quantity - inventory.reserved_quantity
        if available_quantity < quantity:
            return False  # Not enough stock

        inventory.reserved_quantity += quantity
        await self.db.commit()
        return True

    async def release_reservation(self, inventory_id: int, quantity: int) -> bool:
        """Release reserved quantity"""
        inventory = await self.get_inventory_by_id(inventory_id)
        if not inventory:
            return False

        inventory.reserved_quantity = max(0, inventory.reserved_quantity - quantity)
        await self.db.commit()
        return True

    async def fulfill_reservation(self, inventory_id: int, quantity: int) -> bool:
        """Fulfill reservation by reducing both reserved and total quantity"""
        inventory = await self.get_inventory_by_id(inventory_id)
        if not inventory:
            return False

        if inventory.reserved_quantity < quantity:
            return False  # Not enough reserved

        inventory.quantity -= quantity
        inventory.reserved_quantity -= quantity

        # Ensure quantities don't go negative
        inventory.quantity = max(0, inventory.quantity)
        inventory.reserved_quantity = max(0, inventory.reserved_quantity)

        await self.db.commit()
        return True

    async def get_available_quantity(self, inventory_id: int) -> int:
        """Get available quantity (total - reserved)"""
        inventory = await self.get_inventory_by_id(inventory_id)
        if not inventory:
            return 0
        return max(0, inventory.quantity - inventory.reserved_quantity)

    async def delete_inventory(self, inventory_id: int) -> bool:
        """Delete inventory record"""
        inventory = await self.get_inventory_by_id(inventory_id)
        if not inventory:
            return False

        await self.db.delete(inventory)
        await self.db.commit()
        return True
