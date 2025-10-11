from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.order import Order, OrderItem, Status


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_order(
        self,
        user_id: int,
        order_number: str,
        items: List[Dict[str, Any]],
        billing_address: Dict[str, Any],
        shipping_address: Dict[str, Any],
        subtotal: Decimal,
        tax_amount: Decimal,
        shipping_cost: Decimal,
        discount_amount: Decimal,
        total_amount: Decimal,
        currency: str = "USD",
        shipping_method: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Order:
        """Create a new order with items"""

        # Create the order
        order = Order(
            order_number=order_number,
            user_id=user_id,
            status=Status.PENDING.value,
            subtotal=float(subtotal),
            tax_amount=float(tax_amount),
            shipping_cost=float(shipping_cost),
            discount_amount=float(discount_amount),
            total_amount=float(total_amount),
            currency=currency,
            billing_address=billing_address,
            shipping_address=shipping_address,
            shipping_method=shipping_method,
            notes=notes,
        )

        self.session.add(order)
        await self.session.flush()  # Get the order ID

        # Create order items
        for item in items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item["product_id"],
                variant_id=item.get("variant_id"),
                product_name=item["product_name"],
                product_sku=item.get("product_sku"),
                quantity=item["quantity"],
                unit_price=int(Decimal(item["unit_price"]) * 100),  # Store in cents
                total_price=int(Decimal(item["total_price"]) * 100),  # Store in cents
                product_snapshot=item.get("product_snapshot", {}),
            )
            self.session.add(order_item)

        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """Get order by ID with items"""
        query = (
            select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_order_by_number(self, order_number: str) -> Optional[Order]:
        """Get order by order number with items"""
        query = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.order_number == order_number)
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_orders_by_user_id(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        status_filter: Optional[str] = None,
    ) -> Tuple[List[Order], int]:
        """Get orders for a user with optional status filter and return total count"""
        # Get total count
        count_query = select(func.count(Order.id)).where(Order.user_id == user_id)
        if status_filter:
            count_query = count_query.where(Order.status == status_filter)
        count_result = await self.session.execute(count_query)
        total_count = count_result.scalar() or 0

        # Get orders
        query = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.user_id == user_id)
        )

        if status_filter:
            query = query.where(Order.status == status_filter)

        query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        orders = list(result.scalars().all())

        return orders, total_count

    async def update_order_status(
        self,
        order_id: int,
        new_status: str,
        shipped_date: Optional[datetime] = None,
        delivered_date: Optional[datetime] = None,
        canceled_date: Optional[datetime] = None,
    ) -> Optional[Order]:
        """Update order status and related timestamps"""

        # Prepare update data
        update_data: Dict[str, Any] = {"status": new_status}

        if new_status == Status.SHIPPED.value and shipped_date:
            update_data["shipped_date"] = shipped_date
        elif new_status == Status.DELIVERED.value and delivered_date:
            update_data["delivered_date"] = delivered_date
        elif new_status == Status.CANCELED.value and canceled_date:
            update_data["canceled_date"] = canceled_date

        # Update the order
        stmt = update(Order).where(Order.id == order_id).values(**update_data)
        await self.session.execute(stmt)
        await self.session.commit()

        # Return the updated order
        return await self.get_order_by_id(order_id)

    async def update_order(
        self,
        order_id: int,
        update_data: Dict[str, Any],
    ) -> Optional[Order]:
        """Update order with arbitrary data"""
        stmt = update(Order).where(Order.id == order_id).values(**update_data)
        await self.session.execute(stmt)
        await self.session.commit()

        return await self.get_order_by_id(order_id)

    async def delete_order(self, order_id: int) -> bool:
        """Delete an order (soft delete by setting status to canceled)"""
        order = await self.get_order_by_id(order_id)
        if not order:
            return False

        order.status = Status.CANCELED.value
        order.canceled_date = datetime.now(timezone.utc)
        await self.session.commit()
        return True

    async def get_orders_count(
        self, user_id: int, status_filter: Optional[str] = None
    ) -> int:
        """Get total count of orders for a user"""
        query = select(Order).where(Order.user_id == user_id)

        if status_filter:
            query = query.where(Order.status == status_filter)

        result = await self.session.execute(query)
        return len(result.scalars().all())

    async def get_recent_orders(self, limit: int = 10) -> List[Order]:
        """Get most recent orders across all users"""
        query = (
            select(Order)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_orders_by_status(
        self, status: str, skip: int = 0, limit: int = 50
    ) -> List[Order]:
        """Get orders by status"""
        query = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.status == status)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_order_items(self, order_id: int) -> List[OrderItem]:
        """Get all items for an order"""
        query = select(OrderItem).where(OrderItem.order_id == order_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())
