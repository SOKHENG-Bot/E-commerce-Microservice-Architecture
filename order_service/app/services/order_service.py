"""
Order service with comprehensive order management and event publishing.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..events.producers import OrderEventProducer
from ..repository.order_repository import OrderRepository
from ..utils.logging import setup_order_logging as setup_logging

logger = setup_logging("order_service", log_level="INFO")


# Order Status Constants
class OrderStatus:
    """Order status constants"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    FAILED = "failed"


# Business Rules Configuration
class OrderBusinessRules:
    """Business rules for order processing"""

    def __init__(self):
        # Tax and shipping rules (could be moved to settings if needed)
        self.tax_rate = Decimal("0.08")  # 8% tax
        self.free_shipping_threshold = Decimal("50.00")
        self.standard_shipping_cost = Decimal("9.99")
        self.discount_amount = Decimal("0")  # No discount for now

        # Order validation rules
        self.min_order_amount = Decimal("1.00")
        self.max_order_items = 50
        self.max_item_quantity = 99

    def calculate_tax(self, subtotal: Decimal) -> Decimal:
        """Calculate tax amount"""
        return subtotal * self.tax_rate

    def calculate_shipping(self, subtotal: Decimal) -> Decimal:
        """Calculate shipping cost"""
        return (
            Decimal("0")
            if subtotal >= self.free_shipping_threshold
            else self.standard_shipping_cost
        )


class OrderService:
    def __init__(
        self,
        session: Optional[AsyncSession],
        event_publisher: Optional[OrderEventProducer],
    ):
        self.session = session
        self.event_publisher = event_publisher
        self.order_repository = OrderRepository(session) if session else None
        self.business_rules = OrderBusinessRules()

    def _generate_order_number(self, user_id: int) -> str:
        """Generate a unique order number to prevent collisions"""
        import uuid

        # Use UUID for uniqueness instead of timestamp
        unique_id = uuid.uuid4().hex[:12].upper()
        return f"ORD-{unique_id}"

    def _validate_order_data(
        self,
        items: List[Dict[str, Any]],
        billing_address: Dict[str, Any],
        shipping_address: Dict[str, Any],
        total_amount: Decimal,
    ) -> None:
        """Validate order data before creation"""
        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order must contain at least one item",
            )

        if len(items) > self.business_rules.max_order_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order cannot contain more than {self.business_rules.max_order_items} items",
            )

        for item in items:
            if item.get("quantity", 0) <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Item quantity must be greater than 0",
                )
            if item["quantity"] > self.business_rules.max_item_quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item quantity cannot exceed {self.business_rules.max_item_quantity}",
                )

        if total_amount < self.business_rules.min_order_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order total must be at least {self.business_rules.min_order_amount}",
            )

        # Validate required address fields
        required_address_fields = ["street", "city", "state", "zip_code", "country"]
        for field in required_address_fields:
            if field not in billing_address or not billing_address[field]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Billing address missing required field: {field}",
                )
            if field not in shipping_address or not shipping_address[field]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Shipping address missing required field: {field}",
                )

    def _validate_status_transition(self, current_status: str, new_status: str) -> None:
        """Validate that a status transition is allowed"""
        # Define allowed status transitions
        allowed_transitions: Dict[str, List[str]] = {
            OrderStatus.PENDING: [
                OrderStatus.CONFIRMED,
                OrderStatus.CANCELLED,
                OrderStatus.FAILED,
            ],
            OrderStatus.CONFIRMED: [
                OrderStatus.PROCESSING,
                OrderStatus.CANCELLED,
                OrderStatus.FAILED,
            ],
            OrderStatus.PROCESSING: [
                OrderStatus.SHIPPED,
                OrderStatus.CANCELLED,
                OrderStatus.FAILED,
            ],
            OrderStatus.SHIPPED: [
                OrderStatus.DELIVERED,
                OrderStatus.CANCELLED,
                OrderStatus.FAILED,
            ],
            OrderStatus.DELIVERED: [],  # Final state
            OrderStatus.CANCELLED: [],  # Final state
            OrderStatus.REFUNDED: [],  # Final state
            OrderStatus.FAILED: [],  # Final state
        }

        if new_status not in allowed_transitions.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from {current_status} to {new_status}",
            )

    async def create_order(
        self,
        user_id: int,
        items: List[Dict[str, Any]],
        billing_address: Dict[str, Any],
        shipping_address: Dict[str, Any],
        total_amount: Decimal,
        correlation_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a new order with event publishing
        """
        try:
            if not self.order_repository:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database connection not available",
                )

            # Validate order data
            self._validate_order_data(
                items, billing_address, shipping_address, total_amount
            )

            # Generate unique order number
            order_number = self._generate_order_number(user_id)

            # Calculate amounts from items
            subtotal = Decimal("0")
            for item in items:
                item_total = Decimal(str(item["unit_price"])) * item["quantity"]
                subtotal += item_total

            # Apply business rules for tax and shipping
            tax_amount = self.business_rules.calculate_tax(subtotal)
            shipping_cost = self.business_rules.calculate_shipping(subtotal)
            discount_amount = self.business_rules.discount_amount

            # Recalculate total to ensure consistency
            calculated_total = subtotal + tax_amount + shipping_cost - discount_amount

            # Use provided total_amount if it matches calculation (within tolerance)
            if abs(calculated_total - total_amount) > Decimal("0.01"):
                logger.warning(
                    f"Provided total_amount {total_amount} doesn't match calculated {calculated_total}",
                    extra={"user_id": str(user_id), "order_number": order_number},
                )
                # Use calculated total for consistency
                total_amount = calculated_total

            # Create order in database
            order = await self.order_repository.create_order(
                user_id=user_id,
                order_number=order_number,
                items=items,
                billing_address=billing_address,
                shipping_address=shipping_address,
                subtotal=subtotal,
                tax_amount=tax_amount,
                shipping_cost=shipping_cost,
                discount_amount=discount_amount,
                total_amount=total_amount,
            )

            # Publish order created event
            if self.event_publisher:
                await self.event_publisher.publish_order_created(
                    order_id=order.id,
                    order_number=order_number,
                    user_id=user_id,
                    total_amount=total_amount,
                    items=items,
                    billing_address=billing_address,
                    shipping_address=shipping_address,
                    order_data={
                        "status": order.status,
                        "created_at": order.created_at.isoformat(),
                    },
                    correlation_id=correlation_id,
                )

            logger.info(
                "Order created successfully.",
                extra={
                    "order_id": str(order.id),
                    "order_number": order_number,
                    "user_id": str(user_id),
                    "total_amount": str(total_amount),
                    "subtotal": str(subtotal),
                    "tax_amount": str(tax_amount),
                    "shipping_cost": str(shipping_cost),
                },
            )

            return {
                "id": order.id,
                "order_number": order_number,
                "user_id": user_id,
                "total_amount": str(total_amount),
                "subtotal": str(subtotal),
                "tax_amount": str(tax_amount),
                "shipping_cost": str(shipping_cost),
                "discount_amount": str(discount_amount),
                "status": order.status,
                "items": items,
            }

        except HTTPException:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Error creating order for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create order.",
            )

    async def update_order_status(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        old_status: str,
        new_status: str,
        correlation_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Update order status with event publishing
        """
        try:
            if not self.order_repository:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database connection not available",
                )

            # Validate status transition
            self._validate_status_transition(old_status, new_status)

            # Update order status in database
            order = await self.order_repository.update_order_status(
                order_id=order_id,
                new_status=new_status,
            )

            if not order:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Order not found",
                )

            # Publish order status updated event
            if self.event_publisher:
                await self.event_publisher.publish_order_status_updated(
                    order_id=order_id,
                    order_number=order_number,
                    user_id=user_id,
                    old_status=old_status,
                    new_status=new_status,
                    correlation_id=correlation_id,
                )

            logger.info(
                "Order status updated successfully.",
                extra={
                    "order_id": str(order_id),
                    "order_number": order_number,
                    "old_status": old_status,
                    "new_status": new_status,
                },
            )

            return {
                "id": order_id,
                "order_number": order_number,
                "old_status": old_status,
                "new_status": new_status,
            }

        except HTTPException:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Error updating order status {order_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update order status.",
            )

    async def list_orders(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        correlation_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        List orders for a user with pagination
        """
        try:
            if not self.order_repository:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database connection not available",
                )

            # Get orders from database
            orders, total_count = await self.order_repository.get_orders_by_user_id(
                user_id=user_id,
                skip=skip,
                limit=limit,
            )

            # Convert orders to response format
            orders_data: List[Dict[str, Any]] = []
            for order in orders:
                order_dict: Dict[str, Any] = {
                    "id": order.id,
                    "order_number": order.order_number,
                    "user_id": order.user_id,
                    "total_amount": str(order.total_amount),
                    "status": order.status,
                    "created_at": order.created_at.isoformat(),
                    "updated_at": order.updated_at.isoformat(),
                    "items_count": len(order.items) if order.items else 0,
                }
                orders_data.append(order_dict)

            logger.info(
                "Orders listed successfully.",
                extra={
                    "user_id": str(user_id),
                    "total_count": str(total_count),
                    "returned_count": str(len(orders_data)),
                    "skip": str(skip),
                    "limit": str(limit),
                },
            )

            return {
                "orders": orders_data,
                "total": total_count,
                "skip": skip,
                "limit": limit,
            }

        except Exception as e:
            logger.error(f"Error listing orders for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list orders.",
            )

    async def get_order(
        self,
        order_id: int,
        correlation_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get detailed order information
        """
        try:
            if not self.order_repository:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database connection not available",
                )

            # Get order from database
            order = await self.order_repository.get_order_by_id(order_id)
            if not order:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Order not found",
                )

            # Convert order items to response format
            items: List[Dict[str, Any]] = []
            if order.items:
                for item in order.items:
                    try:
                        unit_price = (
                            float(item.unit_price) / 100 if item.unit_price else 0.0
                        )
                        total_price = (
                            float(item.total_price) / 100 if item.total_price else 0.0
                        )
                    except (TypeError, ValueError, AttributeError):
                        unit_price = 0.0
                        total_price = 0.0

                    items.append(
                        {
                            "id": item.id,
                            "product_id": item.product_id,
                            "variant_id": item.variant_id,
                            "product_name": item.product_name,
                            "product_sku": item.product_sku,
                            "quantity": item.quantity,
                            "unit_price": f"{unit_price:.2f}",  # Convert from cents
                            "total_price": f"{total_price:.2f}",  # Convert from cents
                        }
                    )

            # Build response
            def safe_format_float(value: Any, default: str = "0.00") -> str:
                """Safely format a value as float string"""
                try:
                    if value is None:
                        return default
                    return f"{float(value):.2f}"
                except (TypeError, ValueError):
                    return default

            order_data: Dict[str, Any] = {
                "id": order.id,
                "order_number": order.order_number,
                "user_id": order.user_id,
                "status": order.status,
                "total_amount": safe_format_float(order.total_amount),
                "subtotal": safe_format_float(order.subtotal),
                "tax_amount": safe_format_float(order.tax_amount),
                "shipping_cost": safe_format_float(order.shipping_cost),
                "discount_amount": safe_format_float(order.discount_amount),
                "currency": order.currency,
                "created_at": order.created_at.isoformat()
                if order.created_at
                else None,
                "updated_at": order.updated_at.isoformat()
                if order.updated_at
                else None,
                "items": items,
                "billing_address": order.billing_address,
                "shipping_address": order.shipping_address,
                "shipping_method": order.shipping_method,
                "notes": order.notes,
            }

            # Add optional fields if they exist
            if order.shipped_date:
                order_data["shipped_date"] = order.shipped_date.isoformat()
            if order.delivered_date:
                order_data["delivered_date"] = order.delivered_date.isoformat()
            if order.canceled_date:
                order_data["canceled_date"] = order.canceled_date.isoformat()

            logger.info(
                "Order details retrieved successfully.",
                extra={
                    "order_id": str(order_id),
                    "status": str(order.status),
                },
            )

            return order_data

        except Exception as e:
            logger.error(f"Error retrieving order details for {order_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve order details.",
            )
