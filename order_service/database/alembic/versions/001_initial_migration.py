"""Initial migration

Revision ID: 001_initial
Revises:
Create Date: 2024-01-15 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create orders table
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("order_number", sa.String(length=50), unique=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "CONFIRMED",
                "PROCESSING",
                "SHIPPED",
                "DELIVERED",
                "CANCELLED",
                "REFUNDED",
                name="order_status",
            ),
            nullable=False,
        ),
        sa.Column("total_amount", sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column("subtotal", sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column(
            "tax_amount", sa.DECIMAL(precision=10, scale=2), nullable=False, default=0
        ),
        sa.Column(
            "shipping_amount",
            sa.DECIMAL(precision=10, scale=2),
            nullable=False,
            default=0,
        ),
        sa.Column(
            "discount_amount",
            sa.DECIMAL(precision=10, scale=2),
            nullable=False,
            default=0,
        ),
        sa.Column("currency", sa.String(length=3), nullable=False, default="USD"),
        sa.Column(
            "billing_address", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "shipping_address", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("tracking_number", sa.String(length=255), nullable=True),
        sa.Column("estimated_delivery_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_number"),
    )

    # Create order_items table
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("product_sku", sa.String(length=100), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column("total_price", sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column("attributes", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create payments table
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("payment_method", sa.String(length=50), nullable=False),
        sa.Column("payment_provider", sa.String(length=50), nullable=True),
        sa.Column("transaction_id", sa.String(length=255), unique=True, nullable=True),
        sa.Column("amount", sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, default="USD"),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "PROCESSING",
                "COMPLETED",
                "FAILED",
                "REFUNDED",
                "CANCELLED",
                name="payment_status",
            ),
            nullable=False,
        ),
        sa.Column(
            "payment_data", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refund_amount", sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_id"),
    )

    # Create shipping table
    op.create_table(
        "shipping",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("carrier", sa.String(length=100), nullable=True),
        sa.Column("service_type", sa.String(length=100), nullable=True),
        sa.Column("tracking_number", sa.String(length=255), unique=True, nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "SHIPPED",
                "IN_TRANSIT",
                "OUT_FOR_DELIVERY",
                "DELIVERED",
                "FAILED",
                "RETURNED",
                name="shipping_status",
            ),
            nullable=False,
        ),
        sa.Column("shipping_cost", sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column("estimated_delivery_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_delivery_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "shipping_address", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("weight", sa.DECIMAL(precision=8, scale=3), nullable=True),
        sa.Column("dimensions", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("shipping_label_url", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tracking_number"),
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("shipping")
    op.drop_table("payments")
    op.drop_table("order_items")
    op.drop_table("orders")
