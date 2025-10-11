"""Product API endpoints"""

from typing import Optional

from app.api.dependencies import (
    AdminUserDep,
    CorrelationIdDep,
    DatabaseDep,
)
from app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.services.product_service import ProductService
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...utils.logging import setup_product_logging as setup_logging

logger = setup_logging("products_api")
router = APIRouter(prefix="/products")


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
    user_id: str = AdminUserDep,  # Admin authentication required
):
    """Create a new product (admin only)"""

    service = ProductService(db)
    try:
        product = await service.create_product(
            product_data=product_data,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        return product
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Failed to create product: {str(e)}",
            extra={
                "user_id": user_id,
                "correlation_id": correlation_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product",
        )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    request: Request,
    product_id: int,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
):
    """Get product details by ID"""

    service = ProductService(db)
    product = await service.get_product(
        product_id=product_id,
        correlation_id=correlation_id,
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    return product


@router.get("/slug/{slug}", response_model=ProductResponse)
async def get_product_by_slug(
    request: Request,
    slug: str,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
):
    """Get product details by slug"""

    service = ProductService(db)
    product = await service.get_product_by_slug(
        slug=slug,
        correlation_id=correlation_id,
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    return product


@router.get("/sku/{sku}", response_model=ProductResponse)
async def get_product_by_sku(
    request: Request,
    sku: str,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
):
    """Get product details by SKU"""

    service = ProductService(db)
    product = await service.get_product_by_sku(
        sku=sku,
        correlation_id=correlation_id,
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    return product


@router.put("/{product_id}", response_model=ProductResponse)
@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
    user_id: str = AdminUserDep,  # Admin authentication required
):
    """Update product (admin only)"""

    service = ProductService(db)
    try:
        product = await service.update_product(
            product_id=product_id,
            product_data=product_data,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
            )

        return product
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Failed to update product {product_id}: {str(e)}",
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
            detail="Failed to update product",
        )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
    user_id: str = AdminUserDep,  # Admin authentication required
):
    """Delete product (admin only)"""

    service = ProductService(db)
    try:
        success = await service.delete_product(
            product_id=product_id,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
            )

        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to delete product {product_id}: {str(e)}",
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
            detail="Failed to delete product",
        )
