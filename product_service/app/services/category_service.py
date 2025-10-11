"""Category service for business logic"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..events.event_producers import ProductEventProducer
from ..repository.category_repository import CategoryRepository
from ..schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from ..utils.logging import setup_product_logging as setup_logging

# Setup structured logging for the service
logger = setup_logging("category_service")
logger_event = logging.getLogger("category_event")


class CategoryService:
    """Service class for category business logic"""

    def __init__(
        self, db: AsyncSession, event_producer: Optional[ProductEventProducer] = None
    ):
        self.db = db
        self.repository = CategoryRepository(db)
        self.event_producer = event_producer

    async def create_category(
        self,
        category_data: CategoryCreate,
        user_id: str,
        correlation_id: Optional[str] = None,
    ) -> CategoryResponse:
        """Create a new category with validation"""
        try:
            # Validate parent category exists if specified
            if category_data.parent_id:
                parent = await self.repository.get_category_by_id(
                    category_data.parent_id
                )
                if not parent:
                    raise ValueError(
                        f"Parent category {category_data.parent_id} not found"
                    )
                if not parent.is_active:
                    raise ValueError("Cannot create subcategory under inactive parent")

            # Check slug uniqueness
            existing_category = await self.repository.get_category_by_slug(
                category_data.name.lower().replace(" ", "-").replace("_", "-")
            )
            if existing_category:
                raise ValueError("Category with slug already exists")

            # Create category
            category = await self.repository.create_category(category_data)

            logger.info(
                "Category created successfully",
                extra={
                    "category_id": category.id,
                    "category_name": category.name,
                    "parent_id": category.parent_id,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                },
            )

            # Publish category created event
            if self.event_producer:
                await self.event_producer.publish_category_created(
                    category_id=category.id,
                    category_name=category.name,
                    parent_category_id=category.parent_id,
                    correlation_id=int(correlation_id) if correlation_id else None,
                )

            return CategoryResponse(
                id=category.id,
                name=category.name,
                slug=category.slug,
                description=category.description,
                parent_id=category.parent_id,
                image_url=category.image_url,
                is_active=category.is_active,
                sort_order=category.sort_order,
                created_at=category.created_at,
                updated_at=category.updated_at,
            )

        except Exception as e:
            logger.error(
                f"Failed to create category: {str(e)}",
                extra={
                    "category_name": category_data.name,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def get_category(
        self, category_id: int, correlation_id: Optional[str] = None
    ) -> Optional[CategoryResponse]:
        """Get category by ID"""
        category = await self.repository.get_category_by_id(category_id)
        if not category:
            return None

        logger.info(
            "Category retrieved",
            extra={
                "category_id": category_id,
                "correlation_id": correlation_id,
            },
        )

        return CategoryResponse(
            id=category.id,
            name=category.name,
            slug=category.slug,
            description=category.description,
            parent_id=category.parent_id,
            image_url=category.image_url,
            is_active=category.is_active,
            sort_order=category.sort_order,
            created_at=category.created_at,
            updated_at=category.updated_at,
        )

    async def get_category_by_slug(
        self, slug: str, correlation_id: Optional[str] = None
    ) -> Optional[CategoryResponse]:
        """Get category by slug"""
        category = await self.repository.get_category_by_slug(slug)
        if not category:
            return None

        logger.info(
            "Category retrieved by slug",
            extra={
                "slug": slug,
                "category_id": category.id,
                "correlation_id": correlation_id,
            },
        )

        return CategoryResponse(
            id=category.id,
            name=category.name,
            slug=category.slug,
            description=category.description,
            parent_id=category.parent_id,
            image_url=category.image_url,
            is_active=category.is_active,
            sort_order=category.sort_order,
            created_at=category.created_at,
            updated_at=category.updated_at,
        )

    async def update_category(
        self,
        category_id: int,
        category_data: CategoryUpdate,
        user_id: str,
        correlation_id: Optional[str] = None,
    ) -> Optional[CategoryResponse]:
        """Update category"""
        try:
            # Validate parent category if being changed
            if category_data.parent_id is not None:
                if category_data.parent_id == category_id:
                    raise ValueError("Category cannot be its own parent")

                if category_data.parent_id != 0:  # 0 means root level
                    parent = await self.repository.get_category_by_id(
                        category_data.parent_id
                    )
                    if not parent:
                        raise ValueError(
                            f"Parent category {category_data.parent_id} not found"
                        )
                    if not parent.is_active:
                        raise ValueError("Cannot move category under inactive parent")

            category = await self.repository.update_category(category_id, category_data)
            if not category:
                return None

            logger.info(
                "Category updated successfully",
                extra={
                    "category_id": category_id,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                },
            )

            # Publish category updated event
            if self.event_producer:
                updated_fields = category_data.model_dump(exclude_unset=True)
                await self.event_producer.publish_category_updated(
                    category_id=category_id,
                    category_name=category.name,
                    updated_fields=updated_fields,
                    parent_category_id=category.parent_id,
                    correlation_id=int(correlation_id) if correlation_id else None,
                )

            return CategoryResponse(
                id=category.id,
                name=category.name,
                slug=category.slug,
                description=category.description,
                parent_id=category.parent_id,
                image_url=category.image_url,
                is_active=category.is_active,
                sort_order=category.sort_order,
                created_at=category.created_at,
                updated_at=category.updated_at,
            )

        except Exception as e:
            logger.error(
                f"Failed to update category: {str(e)}",
                extra={
                    "category_id": category_id,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def delete_category(
        self, category_id: int, user_id: str, correlation_id: Optional[str] = None
    ) -> bool:
        """Delete category (soft delete)"""
        try:
            success = await self.repository.delete_category(category_id)
            if success:
                logger.info(
                    "Category deleted successfully",
                    extra={
                        "category_id": category_id,
                        "user_id": user_id,
                        "correlation_id": correlation_id,
                    },
                )

                # Publish category deleted event
                if self.event_producer:
                    await self.event_producer.publish_category_deleted(
                        category_id=category_id,
                        correlation_id=int(correlation_id) if correlation_id else None,
                    )

            return success

        except Exception as e:
            logger.error(
                f"Failed to delete category: {str(e)}",
                extra={
                    "category_id": category_id,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise
