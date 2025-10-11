from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OrderItemBase(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(..., gt=0)


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: int
    product_name: str
    product_sku: str
    unit_price: Decimal
    total_price: Decimal


class OrderBase(BaseModel):
    billing_address: dict[str, Any]
    shipping_address: dict[str, Any]
    shipping_method: Optional[str] = None
    notes: Optional[str] = None


class OrderCreate(OrderBase):
    items: List[OrderItemCreate]


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None


class OrderResponse(OrderBase):
    id: int
    order_number: str
    user_id: int
    status: str
    subtotal: Decimal
    tax_amount: Decimal
    shipping_cost: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    currency: str
    items: List[OrderItemResponse]
    order_date: datetime
    created_at: datetime
    updated_at: datetime


# API Schemas for FastAPI endpoints


class OrderItemAPI(BaseModel):
    """Order item model for API"""

    product_id: int
    product_name: str
    quantity: int = Field(gt=0)
    unit_price: Decimal
    total_price: Decimal


class Address(BaseModel):
    """Address model"""

    street: str
    city: str
    state: str
    zip_code: str
    country: str


class CreateOrderRequest(BaseModel):
    """Create order request model"""

    items: List[OrderItemAPI]
    billing_address: Address
    shipping_address: Address
    total_amount: Decimal = Field(gt=0)


class OrderSummary(BaseModel):
    """Order summary model for list responses"""

    id: int
    order_number: str
    user_id: int
    total_amount: str
    status: str
    created_at: str
    updated_at: str
    items_count: int


class OrderListResponse(BaseModel):
    """Order list response model"""

    orders: List[OrderSummary]
    total: int
    skip: int
    limit: int
    message: str


class CreateOrderResponse(BaseModel):
    """Create order response model"""

    id: int
    order_number: str
    user_id: int
    total_amount: str
    subtotal: str
    tax_amount: str
    shipping_cost: str
    discount_amount: str
    status: str
    items: List[Dict[str, Any]]
    message: str


class OrderDetailResponse(BaseModel):
    """Order detail response model"""

    id: int
    order_number: str
    user_id: int
    status: str
    total_amount: str
    subtotal: str
    tax_amount: str
    shipping_cost: str
    discount_amount: str
    currency: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    items: List[Dict[str, Any]]
    billing_address: Dict[str, Any]
    shipping_address: Dict[str, Any]
    shipping_method: Optional[str]
    notes: Optional[str]
    shipped_date: Optional[str] = None
    delivered_date: Optional[str] = None
    canceled_date: Optional[str] = None


class UpdateOrderStatusResponse(BaseModel):
    """Update order status response model"""

    id: int
    order_number: str
    old_status: str
    new_status: str
    updated_at: str
    message: str
