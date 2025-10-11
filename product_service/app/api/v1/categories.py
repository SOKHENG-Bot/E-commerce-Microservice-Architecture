"""Category API endpoints"""

from typing import Optional

from app.api.dependencies import AdminUserDep, CorrelationIdDep, DatabaseDep
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services.category_service import CategoryService
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...utils.logging import setup_product_logging as setup_logging

logger = setup_logging("categories_api")
router = APIRouter(prefix="/categories")


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
    user_id: str = AdminUserDep,  # Admin authentication required
):
    """Create a new category (admin only)"""
    service = CategoryService(db)
    try:
        category = await service.create_category(
            category_data=category_data,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        return category
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Failed to create category: {str(e)}",
            extra={
                "user_id": user_id,
                "correlation_id": correlation_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create category",
        )


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
):
    """Get category details by ID"""
    service = CategoryService(db)
    category = await service.get_category(
        category_id=category_id,
        correlation_id=correlation_id,
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    return category


@router.get("/slug/{slug}", response_model=CategoryResponse)
async def get_category_by_slug(
    slug: str,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
):
    """Get category details by slug"""
    service = CategoryService(db)
    category = await service.get_category_by_slug(
        slug=slug,
        correlation_id=correlation_id,
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    return category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
    user_id: str = AdminUserDep,  # Admin authentication required
):
    """Update category (admin only)"""
    service = CategoryService(db)
    try:
        category = await service.update_category(
            category_id=category_id,
            category_data=category_data,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
            )

        return category
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Failed to update category {category_id}: {str(e)}",
            extra={
                "category_id": category_id,
                "user_id": user_id,
                "correlation_id": correlation_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category",
        )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
    user_id: str = AdminUserDep,  # Admin authentication required
):
    """Delete category (admin only) - soft delete"""
    service = CategoryService(db)
    try:
        # Get category name before deletion for tracking
        existing_category = await service.get_category(
            category_id=category_id,
            correlation_id=correlation_id,
        )

        if not existing_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
            )

        success = await service.delete_category(
            category_id=category_id,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
            )

        return None
    except Exception as e:
        logger.error(
            f"Failed to delete category {category_id}: {str(e)}",
            extra={
                "category_id": category_id,
                "user_id": user_id,
                "correlation_id": correlation_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete category",
        )
