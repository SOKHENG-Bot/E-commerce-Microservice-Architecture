"""
Product Service Event Schemas
=============================

Event data schemas specific to the product service domain.
Imports all schemas from event_schemas.py for clean module structure.
"""

from .event_schemas import (
    CACHE_INVALIDATED,
    CATEGORY_CREATED,
    CATEGORY_DELETED,
    CATEGORY_UPDATED,
    INVENTORY_UPDATED,
    # Constants
    PRODUCT_CREATED,
    PRODUCT_DELETED,
    PRODUCT_SEARCHED,
    PRODUCT_UPDATED,
    PRODUCT_VIEWED,
    REVIEW_CREATED,
    REVIEW_UPDATED,
    SEARCH_PERFORMED,
    # System events
    CacheInvalidationEventData,
    # Category events
    CategoryCreatedEventData,
    CategoryDeletedEventData,
    CategoryEventData,
    CategoryUpdatedEventData,
    InventoryEventData,
    # Inventory events
    InventoryUpdatedEventData,
    # Product events
    ProductCreatedEventData,
    ProductDeletedEventData,
    # Base classes
    ProductEventData,
    ProductSearchEventData,
    ProductUpdatedEventData,
    ProductViewedEventData,
    # Review events
    ReviewCreatedEventData,
    ReviewEventData,
    ReviewUpdatedEventData,
    SearchPerformedEventData,
    # Utility functions
    get_event_producer,
)

__all__ = [
    # Base classes
    "ProductEventData",
    "InventoryEventData",
    "ReviewEventData",
    "CategoryEventData",
    # Product events
    "ProductCreatedEventData",
    "ProductUpdatedEventData",
    "ProductDeletedEventData",
    "ProductViewedEventData",
    "ProductSearchEventData",
    # Inventory events
    "InventoryUpdatedEventData",
    # Review events
    "ReviewCreatedEventData",
    "ReviewUpdatedEventData",
    # Category events
    "CategoryCreatedEventData",
    "CategoryUpdatedEventData",
    "CategoryDeletedEventData",
    # System events
    "CacheInvalidationEventData",
    "SearchPerformedEventData",
    # Constants
    "PRODUCT_CREATED",
    "PRODUCT_UPDATED",
    "PRODUCT_DELETED",
    "PRODUCT_VIEWED",
    "PRODUCT_SEARCHED",
    "INVENTORY_UPDATED",
    "REVIEW_CREATED",
    "REVIEW_UPDATED",
    "CATEGORY_CREATED",
    "CATEGORY_UPDATED",
    "CATEGORY_DELETED",
    "CACHE_INVALIDATED",
    "SEARCH_PERFORMED",
    # Utility functions
    "get_event_producer",
]
