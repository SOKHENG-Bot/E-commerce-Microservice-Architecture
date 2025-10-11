from typing import Any

from sqlalchemy import DECIMAL, JSON, TEXT, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import ProductServiceBaseModel


class Product(ProductServiceBaseModel):
    __tablename__ = "products"

    # Remove id, created_at, updated_at as they're inherited from BaseModel
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    sku: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), nullable=False
    )
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)

    price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    compare_price: Mapped[float | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    cost_price: Mapped[float | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    weight: Mapped[float | None] = mapped_column(DECIMAL(8, 3), nullable=True)

    dimensions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    images: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    meta_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_featured: Mapped[bool] = mapped_column(default=False, nullable=False)
    track_inventory: Mapped[bool] = mapped_column(default=True, nullable=False)


class ProductVariant(ProductServiceBaseModel):
    __tablename__ = "product_variants"

    # Remove id, created_at, updated_at as they're inherited from BaseModel
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)

    price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    compare_price: Mapped[float | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    cost_price: Mapped[float | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    weight: Mapped[float | None] = mapped_column(DECIMAL(8, 3), nullable=True)

    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    images: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
