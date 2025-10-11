"""
Order Service Event Schemas
===========================

Event data schemas specific to the order service domain.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

# ==============================================
# ORDER EVENT DATA SCHEMAS
# ==============================================


class OrderCreatedEventData(BaseModel):
    """Data schema for order creation events"""

    order_id: int
    order_number: str
    user_id: int
    total_amount: Decimal
    items: List[Dict[str, Any]]
    billing_address: Dict[str, Any]
    shipping_address: Dict[str, Any]
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class OrderStatusUpdatedEventData(BaseModel):
    """Data schema for order status update events"""

    order_id: int
    order_number: str
    user_id: int
    old_status: str
    new_status: str
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class OrderCancelledEventData(BaseModel):
    """Data schema for order cancellation events"""

    order_id: int
    order_number: str
    user_id: int
    reason: Optional[str] = None
    cancelled_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class OrderShippedEventData(BaseModel):
    """Data schema for order shipping events"""

    order_id: int
    order_number: str
    user_id: int
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    shipped_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class OrderDeliveredEventData(BaseModel):
    """Data schema for order delivery events"""

    order_id: int
    order_number: str
    user_id: int
    delivered_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class OrderReturnedEventData(BaseModel):
    """Data schema for order return events"""

    order_id: int
    order_number: str
    user_id: int
    reason: Optional[str] = None
    returned_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class OrderRefundedEventData(BaseModel):
    """Data schema for order refund events"""

    order_id: int
    order_number: str
    user_id: int
    refund_amount: Decimal
    reason: Optional[str] = None
    refunded_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


# ==============================================
# EVENT TYPE CONSTANTS
# ==============================================

ORDER_CREATED = "order.created"
ORDER_STATUS_UPDATED = "order.status_updated"
ORDER_CANCELLED = "order.cancelled"
ORDER_SHIPPED = "order.shipped"
ORDER_DELIVERED = "order.delivered"
ORDER_RETURNED = "order.returned"
ORDER_REFUNDED = "order.refunded"
