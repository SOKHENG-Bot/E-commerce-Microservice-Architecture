"""Product service for business logic"""

from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..events.event_producers import ProductEventProducer
from ..repository.product_repository import ProductRepository
from ..schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from ..utils.logging import setup_product_logging as setup_logging

# Setup structured logging for the service
logger = setup_logging("product_service")


class ProductService:
    """Service class for product business logic"""

    def __init__(
        self, db: AsyncSession, event_producer: Optional[ProductEventProducer] = None
    ):
        self.db = db
        self.repository = ProductRepository(db)
        self.event_producer = event_producer

    def _convert_to_product_response(self, product: Any) -> ProductResponse:
        """Helper method to convert database product to ProductResponse with proper type conversions"""
        return ProductResponse(
            id=product.id,
            name=product.name,
            slug=product.slug,
            description=product.description,
            sku=product.sku or "",  # Handle None
            category_id=product.category_id,
            brand=product.brand,
            price=Decimal(str(product.price)),  # Convert float to Decimal
            compare_price=Decimal(str(product.compare_price))
            if product.compare_price is not None
            else None,
            weight=Decimal(str(product.weight)) if product.weight is not None else None,
            dimensions=product.dimensions,
            images=product.images,
            attributes=product.attributes,
            tags=product.tags,
            is_active=product.is_active,
            is_featured=product.is_featured,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )

    async def create_product(
        self,
        product_data: ProductCreate,
        user_id: str,
        correlation_id: Optional[str] = None,
    ) -> ProductResponse:
        """Create a new product"""
        try:
            # Check if SKU already exists
            existing_product = await self.repository.get_product_by_sku(
                product_data.sku
            )
            if existing_product:
                raise ValueError(
                    f"Product with SKU '{product_data.sku}' already exists"
                )

            # Create product
            product = await self.repository.create_product(product_data)

            logger.info(
                "Product created successfully",
                extra={
                    "product_id": product.id,
                    "sku": product.sku,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                },
            )

            # Publish product created event
            if self.event_producer:
                await self.event_producer.publish_product_created(
                    product_id=product.id,
                    name=product.name,
                    sku=product.sku or "",
                    price=float(product.price),
                    category_id=product.category_id,
                    product_data={
                        "description": product.description,
                        "brand": product.brand,
                        "weight": float(product.weight) if product.weight else None,
                        "dimensions": product.dimensions,
                        "images": product.images,
                        "attributes": product.attributes,
                        "tags": product.tags,
                        "is_featured": product.is_featured,
                    },
                    correlation_id=int(correlation_id) if correlation_id else None,
                )

            return self._convert_to_product_response(product)

        except Exception as e:
            logger.error(
                f"Failed to create product: {str(e)}",
                extra={
                    "sku": product_data.sku,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def get_product(
        self, product_id: int, correlation_id: Optional[str] = None
    ) -> Optional[ProductResponse]:
        """Get product by ID"""
        product = await self.repository.get_product_by_id(product_id)
        if not product or not product.is_active:
            return None

        logger.info(
            "Product retrieved",
            extra={
                "product_id": product_id,
                "correlation_id": correlation_id,
            },
        )

        return self._convert_to_product_response(product)

    async def get_product_by_slug(
        self, slug: str, correlation_id: Optional[str] = None
    ) -> Optional[ProductResponse]:
        """Get product by slug"""
        product = await self.repository.get_product_by_slug(slug)
        if not product or not product.is_active:
            return None

        logger.info(
            "Product retrieved by slug",
            extra={
                "slug": slug,
                "product_id": product.id,
                "correlation_id": correlation_id,
            },
        )

        return self._convert_to_product_response(product)

    async def get_product_by_sku(
        self, sku: str, correlation_id: Optional[str] = None
    ) -> Optional[ProductResponse]:
        """Get product by SKU"""
        product = await self.repository.get_product_by_sku(sku)
        if not product or not product.is_active:
            return None

        logger.info(
            "Product retrieved by SKU",
            extra={
                "sku": sku,
                "product_id": product.id,
                "correlation_id": correlation_id,
            },
        )

        return self._convert_to_product_response(product)

    async def update_product(
        self,
        product_id: int,
        product_data: ProductUpdate,
        user_id: str,
        correlation_id: Optional[str] = None,
    ) -> Optional[ProductResponse]:
        """Update product"""
        try:
            product = await self.repository.update_product(product_id, product_data)
            if not product:
                return None

            logger.info(
                "Product updated successfully",
                extra={
                    "product_id": product_id,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                },
            )

            # Publish product updated event
            if self.event_producer:
                updated_fields = product_data.model_dump(exclude_unset=True)
                await self.event_producer.publish_product_updated(
                    product_id=product_id,
                    updated_fields=updated_fields,
                    correlation_id=int(correlation_id) if correlation_id else None,
                )

            return self._convert_to_product_response(product)

        except Exception as e:
            logger.error(
                f"Failed to update product: {str(e)}",
                extra={
                    "product_id": product_id,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def delete_product(
        self, product_id: int, user_id: str, correlation_id: Optional[str] = None
    ) -> bool:
        """Delete product (soft delete)"""
        try:
            # Get product data before deletion for event
            product = await self.repository.get_product_by_id(product_id)

            success = await self.repository.delete_product(product_id)
            if success and product:
                logger.info(
                    "Product deleted successfully",
                    extra={
                        "product_id": product_id,
                        "user_id": user_id,
                        "correlation_id": correlation_id,
                    },
                )

                # Publish product deleted event
                if self.event_producer:
                    product_data: Dict[str, Any] = {
                        "name": product.name,
                        "sku": product.sku or "",
                        "category_id": product.category_id,
                        "price": float(product.price),
                        "description": product.description,
                        "brand": product.brand,
                        "is_active": product.is_active,
                        "is_featured": product.is_featured,
                    }
                    await self.event_producer.publish_product_deleted(
                        product_id=product_id,
                        product_data=product_data,
                        correlation_id=int(correlation_id) if correlation_id else None,
                    )

            return success

        except Exception as e:
            logger.error(
                f"Failed to delete product: {str(e)}",
                extra={
                    "product_id": product_id,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise
