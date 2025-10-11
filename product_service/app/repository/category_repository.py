"""Category repository for database operations"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.category import Category
from ..schemas.category import CategoryCreate, CategoryUpdate


class CategoryRepository:
    """Repository for category database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_category(self, category_data: CategoryCreate) -> Category:
        """Create a new category"""
        # Generate slug from name
        slug = category_data.name.lower().replace(" ", "-").replace("_", "-")

        category = Category(
            name=category_data.name,
            slug=slug,
            description=category_data.description,
            parent_id=category_data.parent_id,
            image_url=category_data.image_url,
            is_active=category_data.is_active,
            sort_order=category_data.sort_order or 0,
        )

        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """Get category by ID"""
        query = select(Category).where(Category.id == category_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_category_by_slug(self, slug: str) -> Optional[Category]:
        """Get category by slug"""
        query = select(Category).where(Category.slug == slug)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_category(
        self, category_id: int, category_data: CategoryUpdate
    ) -> Optional[Category]:
        """Update category"""
        category = await self.get_category_by_id(category_id)
        if not category:
            return None

        update_data = category_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "name" and value:
                # Update slug when name changes
                setattr(
                    category, "slug", value.lower().replace(" ", "-").replace("_", "-")
                )
            setattr(category, field, value)

        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def delete_category(self, category_id: int) -> bool:
        """Delete category (soft delete by setting is_active=False)"""
        category = await self.get_category_by_id(category_id)
        if not category:
            return False

        category.is_active = False
        await self.db.commit()
        return True
