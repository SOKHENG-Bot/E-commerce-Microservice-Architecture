from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status

from ...schemas.order import (
    CreateOrderRequest,
    CreateOrderResponse,
    OrderDetailResponse,
    OrderListResponse,
    UpdateOrderStatusResponse,
)
from ...services.order_service import OrderService
from ..deps import (
    CorrelationIdDep,
    CurrentUserIdDep,
    CurrentUserRoleDep,
    OrderServiceDep,
)


def parse_correlation_id(correlation_id: Optional[str]) -> Optional[int]:
    """Parse correlation ID to integer if valid"""
    if correlation_id and correlation_id.isdigit():
        return int(correlation_id)
    return None


def validate_order_id(order_id: str) -> int:
    """Validate and parse order ID"""
    if not order_id.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID format",
        )
    return int(order_id)


router = APIRouter(prefix="/orders")


@router.get("/", status_code=status.HTTP_200_OK)
async def list_orders(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of orders to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of orders to return"),
    correlation_id: Optional[str] = CorrelationIdDep,
    user_id: str = CurrentUserIdDep,  # ← User ID from middleware
    order_service: OrderService = OrderServiceDep,
) -> OrderListResponse:
    """List user orders with pagination"""
    try:
        # Get orders using service
        result: Dict[str, Any] = await order_service.list_orders(  # type: ignore
            user_id=int(user_id),  # Convert to int for service
            skip=skip,
            limit=limit,
            correlation_id=parse_correlation_id(correlation_id),
        )

        return OrderListResponse(
            orders=result["orders"],
            total=result["total"],
            skip=result["skip"],
            limit=result["limit"],
            message=f"Retrieved {len(result['orders'])} orders for user {user_id}",
        )

    except HTTPException:
        # Re-raise HTTP exceptions from service
        raise
    except Exception:
        # Log the error and return generic error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve orders",
        )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_order(
    request: Request,
    order_data: CreateOrderRequest,
    correlation_id: Optional[str] = CorrelationIdDep,
    user_id: str = CurrentUserIdDep,  # ← User ID from middleware
    order_service: OrderService = OrderServiceDep,
) -> CreateOrderResponse:
    """Create a new order"""
    try:
        # Create order using service
        result: Dict[str, Any] = await order_service.create_order(  # type: ignore
            user_id=int(user_id),  # Convert to int for service
            items=[item.model_dump() for item in order_data.items],
            billing_address=order_data.billing_address.model_dump(),
            shipping_address=order_data.shipping_address.model_dump(),
            total_amount=order_data.total_amount,
            correlation_id=parse_correlation_id(correlation_id),
        )

        return CreateOrderResponse(
            id=result["id"],
            order_number=result["order_number"],
            user_id=result["user_id"],
            total_amount=result["total_amount"],
            subtotal=result["subtotal"],
            tax_amount=result["tax_amount"],
            shipping_cost=result["shipping_cost"],
            discount_amount=result["discount_amount"],
            status=result["status"],
            items=result["items"],
            message="Order created successfully",
        )

    except HTTPException:
        # Re-raise HTTP exceptions from service
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order",
        )


@router.get("/{order_id}", status_code=status.HTTP_200_OK)
async def get_order(
    request: Request,
    order_id: str,
    correlation_id: Optional[str] = CorrelationIdDep,
    user_id: str = CurrentUserIdDep,  # ← User ID from middleware
    user_role: Optional[str] = CurrentUserRoleDep,  # ← User role from middleware
    order_service: OrderService = OrderServiceDep,
) -> OrderDetailResponse:
    """Get order details by ID"""
    try:
        # Validate and parse order_id
        order_id_int = validate_order_id(order_id)

        # Get order details using service
        order: Dict[str, Any] = await order_service.get_order(  # type: ignore
            order_id=order_id_int,
            correlation_id=parse_correlation_id(correlation_id),
        )

        # Check ownership: users can only view their own orders, admins can view any
        user_id_int = int(user_id)
        order_owner_id = order.get("user_id")

        if user_role != "admin" and user_id_int != order_owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own orders",
            )

        return OrderDetailResponse(**order)

    except HTTPException:
        # Re-raise HTTP exceptions from service
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve order",
        )


@router.put("/{order_id}/status", status_code=status.HTTP_200_OK)
async def update_order_status(
    request: Request,
    order_id: str,
    new_status: str = Query(..., description="New order status"),
    correlation_id: Optional[str] = CorrelationIdDep,
    user_id: str = CurrentUserIdDep,  # ← User ID from middleware
    user_role: Optional[str] = CurrentUserRoleDep,  # ← User role from middleware
    order_service: OrderService = OrderServiceDep,
) -> UpdateOrderStatusResponse:
    """Update order status"""
    try:
        # Validate and parse order_id
        order_id_int = validate_order_id(order_id)

        # Get current order to retrieve actual status and order number
        current_order = await order_service.get_order(order_id_int)
        old_status = current_order.get("status", "pending")
        order_number = current_order.get("order_number", f"ORD-{order_id_int}")

        # Check ownership: users can only update their own orders, admins can update any
        user_id_int = int(user_id)
        order_owner_id = current_order.get("user_id")

        if user_role != "admin" and user_id_int != order_owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own orders",
            )

        # Update order status using service
        result: Dict[str, Any] = await order_service.update_order_status(  # type: ignore
            order_id=order_id_int,
            order_number=order_number,
            user_id=user_id_int,
            old_status=old_status,
            new_status=new_status,
            correlation_id=parse_correlation_id(correlation_id),
        )

        # Get the updated timestamp from the result or current time
        updated_at = result.get(
            "updated_at", current_order.get("updated_at", "2024-01-01T00:00:00Z")
        )

        return UpdateOrderStatusResponse(
            id=result["id"],
            order_number=result["order_number"],
            old_status=result["old_status"],
            new_status=result["new_status"],
            updated_at=updated_at,
            message=f"Order status updated from {old_status} to {new_status}",
        )

    except HTTPException:
        # Re-raise HTTP exceptions from service
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update order status",
        )
