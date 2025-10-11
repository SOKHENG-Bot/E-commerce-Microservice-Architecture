from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import DECIMAL, JSON, TEXT, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import OrderServiceBaseModel


class Status(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELED = "canceled"


class Order(OrderServiceBaseModel):
    __tablename__ = "orders"

    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Reference to user service (no FK in microservices)

    status: Mapped[str] = mapped_column(
        String(20), default=Status.PENDING.value, nullable=False
    )
    subtotal: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(DECIMAL(10, 2), default=0, nullable=False)
    shipping_cost: Mapped[float] = mapped_column(
        DECIMAL(10, 2), default=0, nullable=False
    )
    discount_amount: Mapped[float] = mapped_column(
        DECIMAL(10, 2), default=0, nullable=False
    )
    total_amount: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    billing_address: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    shipping_address: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    shipping_method: Mapped[str | None] = mapped_column(String(100), nullable=True)

    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    shipped_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    canceled_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(TEXT, nullable=True)

    # Relationship with order items
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(OrderServiceBaseModel):
    __tablename__ = "order_items"

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Reference to product service (no FK in microservices)
    variant_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # Reference to product service (no FK in microservices)

    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price: Mapped[int] = mapped_column(Integer, nullable=False)
    product_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Relationship with order
    order: Mapped["Order"] = relationship("Order", back_populates="items")
