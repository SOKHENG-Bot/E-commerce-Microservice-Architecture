"""
Product Service Event Schemas
=============================

Event data schemas specific to the product service domain.
Consolidated from multiple files to eliminate duplication.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from pydantic import BaseModel

# ==============================================
# BASE EVENT DATA CLASSES
# ==============================================


class ProductEventData(BaseModel):
    """Base product event data structure"""

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class InventoryEventData(BaseModel):
    """Base inventory event data structure"""

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ReviewEventData(BaseModel):
    """Base review event data structure"""

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class CategoryEventData(BaseModel):
    """Base category event data structure"""

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


# ==============================================
# PRODUCT EVENT DATA SCHEMAS
# ==============================================


class ProductCreatedEventData(ProductEventData):
    """Data schema for product creation events"""

    product_id: int
    name: str
    sku: str
    price: Decimal
    category_id: int
    description: Optional[str] = None
    brand: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ProductUpdatedEventData(ProductEventData):
    """Data schema for product update events"""

    product_id: int
    updated_fields: Dict[str, Any]
    previous_values: Optional[Dict[str, Any]] = None
    updated_at: datetime


class ProductDeletedEventData(ProductEventData):
    """Data schema for product deletion events"""

    product_id: int
    name: str
    sku: str
    deleted_at: datetime


class ProductViewedEventData(ProductEventData):
    """Data for product view tracking events"""

    product_id: int
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    viewed_at: datetime
    referrer: Optional[str] = None


class ProductSearchEventData(BaseModel):
    """Data for product search events"""

    search_query: str
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    results_count: int
    filters_applied: Optional[Dict[str, Any]] = None
    searched_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


# ==============================================
# INVENTORY EVENT DATA SCHEMAS
# ==============================================


class InventoryUpdatedEventData(InventoryEventData):
    """Data schema for inventory update events"""

    product_id: int
    variant_id: Optional[int] = None
    quantity: int
    reserved_quantity: int
    previous_quantity: int
    warehouse_id: Optional[int] = None
    updated_at: datetime
    reason: Optional[str] = None


# ==============================================
# REVIEW EVENT DATA SCHEMAS
# ==============================================


class ReviewCreatedEventData(ReviewEventData):
    """Data for review creation events"""

    review_id: int
    product_id: int
    user_id: int
    rating: int
    title: str
    content: str
    is_verified_purchase: Optional[bool] = None
    created_at: datetime


class ReviewUpdatedEventData(ReviewEventData):
    """Data for review update events"""

    review_id: int
    product_id: int
    user_id: int
    updated_fields: Dict[str, Any]
    previous_values: Optional[Dict[str, Any]] = None
    updated_at: datetime


# ==============================================
# CATEGORY EVENT DATA SCHEMAS
# ==============================================


class CategoryCreatedEventData(CategoryEventData):
    """Data schema for category creation events"""

    category_id: int
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    created_at: datetime
    created_by: Optional[int] = None


class CategoryUpdatedEventData(CategoryEventData):
    """Data schema for category update events"""

    category_id: int
    name: str
    updated_fields: Dict[str, Any]
    parent_id: Optional[int] = None
    updated_at: datetime
    updated_by: Optional[int] = None


class CategoryDeletedEventData(CategoryEventData):
    """Data for category deletion events"""

    category_id: int
    deleted_at: datetime


# ==============================================
# SYSTEM EVENT DATA SCHEMAS
# ==============================================


class CacheInvalidationEventData(BaseModel):
    """Data for cache invalidation events"""

    cache_type: str
    pattern: str
    keys_invalidated: int
    invalidated_at: float

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class SearchPerformedEventData(BaseModel):
    """Data for search performed events"""

    search_query: str
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    results_count: int
    filters_applied: Optional[Dict[str, Any]] = None
    searched_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


# ==============================================
# EVENT TYPE CONSTANTS
# ==============================================

# Product Events
PRODUCT_CREATED = "product.created"
PRODUCT_UPDATED = "product.updated"
PRODUCT_DELETED = "product.deleted"
PRODUCT_VIEWED = "product.viewed"
PRODUCT_SEARCHED = "product.searched"

# Inventory Events
INVENTORY_UPDATED = "inventory.updated"

# Review Events
REVIEW_CREATED = "review.created"
REVIEW_UPDATED = "review.updated"

# Category Events
CATEGORY_CREATED = "category.created"
CATEGORY_UPDATED = "category.updated"
CATEGORY_DELETED = "category.deleted"

# System Events
CACHE_INVALIDATED = "cache.invalidated"
SEARCH_PERFORMED = "search.performed"


def get_event_producer():
    """
    Get the event producer for the product service.
    Returns None if event publishing is disabled or unavailable.
    """
    # For unit tests and when event publishing is not needed, return None
    # In production, this would initialize the actual producer
    return None
