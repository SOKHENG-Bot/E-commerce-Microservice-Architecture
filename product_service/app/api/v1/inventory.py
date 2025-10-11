"""Inventory API endpoints"""

import uuid
from typing import Any, Dict, Optional

from app.api.dependencies import (
    AdminUserDep,
    AuthenticatedUserDep,
    CorrelationIdDep,
    DatabaseDep,
)
from app.schemas.inventory import (
    InventoryAdjustment,
    InventoryCreate,
    InventoryResponse,
    InventoryUpdate,
)
from app.services.inventory_service import InventoryService
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...utils.logging import setup_product_logging as setup_logging

logger = setup_logging("inventory_api")
router = APIRouter(prefix="/inventory")


@router.get("/products/{product_id}", response_model=InventoryResponse)
async def get_product_inventory(
    product_id: int,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
):
    """Get inventory for a specific product"""
    service = InventoryService(db)
    inventory = await service.get_inventory_by_product(
        product_id=product_id,
        correlation_id=correlation_id,
    )

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found for this product",
        )

    return inventory


@router.get("/variants/{variant_id}", response_model=InventoryResponse)
async def get_variant_inventory(
    variant_id: int,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
):
    """Get inventory for a specific variant"""
    service = InventoryService(db)
    inventory = await service.get_inventory_by_variant(
        variant_id=variant_id,
        correlation_id=correlation_id,
    )

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found for this variant",
        )

    return inventory


@router.get("/{inventory_id}", response_model=InventoryResponse)
async def get_inventory(
    inventory_id: int,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
):
    """Get inventory by ID"""
    service = InventoryService(db)
    inventory = await service.get_inventory_by_id(
        inventory_id=inventory_id,
        correlation_id=correlation_id,
    )

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory not found"
        )

    return inventory


@router.get("/{inventory_id}/available", response_model=Dict[str, int])
async def get_available_quantity(
    inventory_id: int,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
):
    """Get available quantity for inventory"""
    service = InventoryService(db)
    available_quantity = await service.get_available_quantity(
        inventory_id=inventory_id,
        correlation_id=correlation_id,
    )

    return {"available_quantity": available_quantity}


@router.post(
    "/products/{product_id}",
    response_model=InventoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product_inventory(
    product_id: int,
    inventory_data: InventoryCreate,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
    user_id: str = AdminUserDep,  # Admin authentication required
):
    """Create inventory for a product (admin only)"""
    # Set the product_id from URL
    inventory_data.product_id = product_id

    service = InventoryService(db)
    try:
        inventory = await service.create_inventory(
            inventory_data=inventory_data,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        return inventory
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Failed to create inventory for product {product_id}: {str(e)}",
            extra={
                "product_id": product_id,
                "user_id": user_id,
                "correlation_id": correlation_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create inventory",
        )


@router.put("/{inventory_id}", response_model=InventoryResponse)
async def update_inventory(
    inventory_id: int,
    inventory_data: InventoryUpdate,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
    user_id: str = AdminUserDep,  # Admin authentication required
):
    """Update inventory (admin only)"""
    service = InventoryService(db)
    try:
        inventory = await service.update_inventory(
            inventory_id=inventory_id,
            inventory_data=inventory_data,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        if not inventory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Inventory not found"
            )

        return inventory
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Failed to update inventory {inventory_id}: {str(e)}",
            extra={
                "inventory_id": inventory_id,
                "user_id": user_id,
                "correlation_id": correlation_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update inventory",
        )


@router.post("/{inventory_id}/adjust", response_model=InventoryResponse)
async def adjust_inventory(
    inventory_id: int,
    adjustment: InventoryAdjustment,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
    user_id: str = AdminUserDep,  # Admin authentication required
):
    """Adjust inventory quantity (admin only)"""
    service = InventoryService(db)
    try:
        inventory = await service.adjust_quantity(
            inventory_id=inventory_id,
            adjustment=adjustment,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        if not inventory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Inventory not found"
            )

        return inventory
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Failed to adjust inventory {inventory_id}: {str(e)}",
            extra={
                "inventory_id": inventory_id,
                "adjustment": adjustment.model_dump(),
                "user_id": user_id,
                "correlation_id": correlation_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to adjust inventory",
        )


@router.post("/{inventory_id}/reserve")
async def reserve_inventory(
    inventory_id: int,
    quantity: int = Query(..., ge=1, description="Quantity to reserve"),
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
    user_id: str = AuthenticatedUserDep,  # User authentication required
) -> Dict[str, Any]:
    """Reserve inventory for an order"""
    service = InventoryService(db)
    try:
        success = await service.reserve_quantity(
            inventory_id=inventory_id,
            quantity=quantity,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to reserve inventory",
            )

        # Generate a simple reservation ID for response
        reservation_id = str(uuid.uuid4())

        return {
            "reservation_id": reservation_id,
            "inventory_id": inventory_id,
            "quantity": quantity,
            "message": "Inventory reserved successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Failed to reserve inventory {inventory_id}: {str(e)}",
            extra={
                "inventory_id": inventory_id,
                "quantity": quantity,
                "user_id": user_id,
                "correlation_id": correlation_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reserve inventory",
        )


@router.post("/{inventory_id}/release")
async def release_reservation(
    inventory_id: int,
    quantity: int = Query(..., ge=1, description="Quantity to release"),
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
    user_id: str = AuthenticatedUserDep,  # User authentication required
) -> Dict[str, Any]:
    """Release reserved inventory"""
    service = InventoryService(db)
    try:
        success = await service.release_reservation(
            inventory_id=inventory_id,
            quantity=quantity,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to release reservation",
            )

        return {
            "inventory_id": inventory_id,
            "quantity": quantity,
            "message": "Reservation released successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Failed to release reservation for inventory {inventory_id}: {str(e)}",
            extra={
                "inventory_id": inventory_id,
                "quantity": quantity,
                "user_id": user_id,
                "correlation_id": correlation_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to release reservation",
        )


@router.post("/reservations/{reservation_id}/fulfill")
async def fulfill_reservation(
    reservation_id: str,
    inventory_id: int = Query(..., description="Inventory ID to fulfill"),
    quantity: int = Query(..., ge=1, description="Quantity to fulfill"),
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
    user_id: str = AuthenticatedUserDep,  # User authentication required
) -> Dict[str, Any]:
    """Fulfill an inventory reservation"""
    service = InventoryService(db)
    try:
        success = await service.fulfill_reservation(
            inventory_id=inventory_id,
            quantity=quantity,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fulfill reservation",
            )

        return {
            "reservation_id": reservation_id,
            "inventory_id": inventory_id,
            "quantity": quantity,
            "message": "Reservation fulfilled successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Failed to fulfill reservation {reservation_id}: {str(e)}",
            extra={
                "reservation_id": reservation_id,
                "inventory_id": inventory_id,
                "quantity": quantity,
                "user_id": user_id,
                "correlation_id": correlation_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fulfill reservation",
        )


@router.delete("/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory(
    inventory_id: int,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
    user_id: str = AdminUserDep,  # Admin authentication required
):
    """Delete inventory (admin only)"""
    service = InventoryService(db)
    try:
        success = await service.delete_inventory(
            inventory_id=inventory_id,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Inventory not found"
            )

        return None
    except Exception as e:
        logger.error(
            f"Failed to delete inventory {inventory_id}: {str(e)}",
            extra={
                "inventory_id": inventory_id,
                "user_id": user_id,
                "correlation_id": correlation_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete inventory",
        )
