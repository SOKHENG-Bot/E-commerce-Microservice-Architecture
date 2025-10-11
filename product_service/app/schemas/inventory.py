from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InventoryBase(BaseModel):
    quantity: int = Field(default=0, ge=0)
    reserved_quantity: int = Field(default=0, ge=0)
    reorder_level: Optional[int] = Field(default=0, ge=0)
    warehouse_location: Optional[str] = None


class InventoryCreate(InventoryBase):
    product_id: Optional[int] = None
    variant_id: Optional[int] = None


class InventoryUpdate(BaseModel):
    quantity: Optional[int] = Field(default=None, ge=0)
    reserved_quantity: Optional[int] = Field(default=None, ge=0)
    reorder_level: Optional[int] = Field(default=None, ge=0)
    warehouse_location: Optional[str] = None


class InventoryResponse(InventoryBase):
    id: int
    product_id: Optional[int] = None
    variant_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    @property
    def available_quantity(self) -> int:
        """Calculate available quantity (total - reserved)"""
        return max(0, self.quantity - self.reserved_quantity)
    
    @property
    def is_low_stock(self) -> bool:
        """Check if item is low stock"""
        if self.reorder_level is None:
            return False
        return self.available_quantity <= self.reorder_level


class InventoryAdjustment(BaseModel):
    """Schema for inventory quantity adjustments"""
    quantity_change: int = Field(..., description="Positive for increase, negative for decrease")
    reason: str = Field(default="manual_adjustment", max_length=255)


class BulkInventoryUpdate(BaseModel):
    """Schema for bulk inventory updates"""
    inventory_id: int
    quantity: int = Field(ge=0)


class InventoryStats(BaseModel):
    """Inventory statistics schema"""
    total_items: int
    low_stock_items: int
    out_of_stock_items: int
    total_value: float
