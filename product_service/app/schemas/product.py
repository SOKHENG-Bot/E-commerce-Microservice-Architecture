from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class ProductBase(BaseModel):
    name: str = Field(
        ..., min_length=1, description="Product name (required, non-empty)"
    )
    description: Optional[str] = None
    short_description: Optional[str] = None
    sku: str
    category_id: int = Field(..., gt=0, description="Category ID (must be positive)")
    brand: Optional[str] = None
    price: Decimal = Field(..., gt=0, description="Product price (must be positive)")
    compare_price: Optional[Decimal] = Field(
        None, gt=0, description="Compare price (must be positive if provided)"
    )
    weight: Optional[Decimal] = Field(
        None, ge=0, description="Product weight (must be non-negative if provided)"
    )
    dimensions: Optional[dict[str, Any]] = None
    images: Optional[List[str]] = []
    attributes: Optional[dict[str, Any]] = {}
    tags: Optional[List[str]] = []
    is_active: bool = True
    is_featured: bool = False

    @field_validator("price", "compare_price", "weight")
    @classmethod
    def validate_positive_values(cls, v, info):
        if v is not None and v < 0:
            raise ValueError(f"{info.field_name} must be non-negative")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("name cannot be empty or whitespace only")
        return v.strip()

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, v):
        if not v or not v.strip():
            raise ValueError("sku cannot be empty or whitespace only")
        return v.strip().upper()


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    is_active: Optional[bool] = None
    # ... other optional fields


class ProductResponse(ProductBase):
    id: int
    slug: str
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    products: List[ProductResponse]
    total: int
    page: int
    size: int
    total_pages: int
