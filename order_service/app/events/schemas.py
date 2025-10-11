"""
Order service event schemas for order and payment related events.
Provides data structures that work with local events.base.BaseEvent infrastructure.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

# Event type constants
ORDER_CREATED = "order.created"
ORDER_STATUS_UPDATED = "order.status_updated"
ORDER_CANCELLED = "order.cancelled"
ORDER_FULFILLED = "order.fulfilled"
ORDER_DELIVERED = "order.delivered"
PAYMENT_PROCESSED = "payment.processed"
PAYMENT_FAILED = "payment.failed"
REFUND_PROCESSED = "refund.processed"
CART_ITEM_ADDED = "cart.item_added"
CART_ITEM_REMOVED = "cart.item_removed"
CART_CLEARED = "cart.cleared"


class OrderEventData(BaseModel):
    """Base order event data structure"""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for BaseEvent compatibility"""
        return self.model_dump()


class OrderCreatedEventData(OrderEventData):
    """Data for order creation events"""

    order_id: int
    order_number: str
    user_id: int
    total_amount: Decimal
    items: List[Dict[str, Any]]
    billing_address: Dict[str, Any]
    shipping_address: Dict[str, Any]
    status: str
    payment_status: str
    created_at: datetime


class OrderStatusUpdatedEventData(OrderEventData):
    """Data for order status update events"""

    order_id: int
    order_number: str
    user_id: int
    old_status: str
    new_status: str
    updated_at: datetime
    reason: Optional[str] = None


class OrderCancelledEventData(OrderEventData):
    """Data for order cancellation events"""

    order_id: int
    order_number: str
    user_id: int
    reason: str
    refund_amount: Optional[Decimal] = None
    cancelled_at: datetime


class OrderFulfilledEventData(OrderEventData):
    """Data for order fulfillment events"""

    order_id: int
    order_number: str
    user_id: int
    tracking_number: Optional[str] = None
    fulfilled_at: datetime


class OrderDeliveredEventData(OrderEventData):
    """Data for order delivery events"""

    order_id: int
    order_number: str
    user_id: int
    delivered_at: datetime
    delivery_confirmed_by: Optional[str] = None


class PaymentEventData(BaseModel):
    """Base payment event data structure"""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for BaseEvent compatibility"""
        return self.model_dump()


class PaymentProcessedEventData(PaymentEventData):
    """Data for payment processing events"""

    payment_id: int
    order_id: int
    user_id: int
    amount: Decimal
    payment_method: str
    status: str
    transaction_id: Optional[str] = None
    processed_at: datetime


class PaymentFailedEventData(PaymentEventData):
    """Data for payment failure events"""

    payment_id: int
    order_id: int
    user_id: int
    amount: Decimal
    payment_method: str
    error_reason: str
    error_code: Optional[str] = None
    failed_at: datetime


class RefundProcessedEventData(PaymentEventData):
    """Data for refund processing events"""

    refund_id: int
    payment_id: int
    order_id: int
    user_id: int
    refund_amount: Decimal
    reason: str
    refund_method: Optional[str] = None
    processed_at: datetime


class CartEventData(BaseModel):
    """Base cart event data structure"""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for BaseEvent compatibility"""
        return self.model_dump()


class CartItemAddedEventData(CartEventData):
    """Data for cart item addition events"""

    user_id: int
    product_id: int
    variant_id: Optional[int] = None
    quantity: int
    price: Decimal
    added_at: datetime


class CartItemRemovedEventData(CartEventData):
    """Data for cart item removal events"""

    user_id: int
    product_id: int
    variant_id: Optional[int] = None
    removed_at: datetime


class CartClearedEventData(CartEventData):
    """Data for cart clearing events"""

    user_id: int
    cleared_at: datetime
    item_count: Optional[int] = None


class OrderItemData(BaseModel):
    """Data structure for order items"""

    product_id: int
    variant_id: Optional[int] = None
    quantity: int
    price: Decimal
    total: Decimal
    product_name: str
    sku: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for BaseEvent compatibility"""
        return self.model_dump()


class AddressData(BaseModel):
    """Data structure for addresses"""

    street: str
    city: str
    state: str
    postal_code: str
    country: str
    recipient_name: Optional[str] = None
    phone: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for BaseEvent compatibility"""
        return self.model_dump()


class ShippingEventData(BaseModel):
    """Data for shipping-related events"""

    order_id: int
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    status: str
    estimated_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for BaseEvent compatibility"""
        return self.model_dump()


class OrderIssueEventData(OrderEventData):
    """Data for order issue events"""

    order_id: int
    issue_type: str
    issue_details: str
    severity: str = "medium"  # low, medium, high, critical
    flagged_at: datetime
    resolved: bool = False
