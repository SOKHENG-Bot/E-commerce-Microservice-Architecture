"""Product repository for database operations"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.product import Product
from ..schemas.product import ProductCreate, ProductUpdate


class ProductRepository:
    """Repository for product database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_product(self, product_data: ProductCreate) -> Product:
        """Create a new product"""
        # Generate slug from name
        slug = product_data.name.lower().replace(" ", "-").replace("_", "-")

        product = Product(
            name=product_data.name,
            slug=slug,
            description=product_data.description,
            sku=product_data.sku,
            category_id=product_data.category_id,
            brand=product_data.brand,
            price=product_data.price,
            compare_price=product_data.compare_price,
            weight=product_data.weight,
            dimensions=product_data.dimensions,
            images=product_data.images,
            attributes=product_data.attributes,
            tags=product_data.tags,
            is_active=product_data.is_active,
            is_featured=product_data.is_featured,
        )

        self.db.add(product)
        await self.db.commit()
        await self.db.refresh(product)
        return product

    async def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID"""
        query = select(Product).where(Product.id == product_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_product_by_slug(self, slug: str) -> Optional[Product]:
        """Get product by slug"""
        query = select(Product).where(Product.slug == slug)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_product_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU"""
        query = select(Product).where(Product.sku == sku)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_product(
        self, product_id: int, product_data: ProductUpdate
    ) -> Optional[Product]:
        """Update product"""
        product = await self.get_product_by_id(product_id)
        if not product:
            return None

        update_data = product_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)

        await self.db.commit()
        await self.db.refresh(product)
        return product

    async def delete_product(self, product_id: int) -> bool:
        """Delete product (soft delete by setting is_active=False)"""
        product = await self.get_product_by_id(product_id)
        if not product:
            return False

        product.is_active = False
        await self.db.commit()
        return True
