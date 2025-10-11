"""
Events module for the Product Service.

This module contains event producers and consumers for handling
product-related events in the microservices architecture.

Producers:
    - ProductEventProducer: Publishes product lifecycle events
    - Product events: Create, update, delete, price changes, status changes
    - Inventory events: Stock updates, alerts, and replenishment
    - Category events: Category management and changes
    - Bulk operations: Import/export, bulk updates, batch processing
    - Error events: Sync failures, validation errors, system alerts

Consumers:
    - OrderCreatedHandler: Reserves inventory for new orders
    - OrderFulfilledHandler: Deducts inventory for completed orders
    - ProductViewedHandler: Tracks product analytics
    - BulkOperationHandler: Monitors bulk operation completions
    - ErrorEventHandler: Handles system error alerts and monitoring

Event Types Supported:
    Core Events: product_created, product_updated, product_deleted,
                product_price_changed, product_status_changed,
                inventory_updated, low_stock_alert, out_of_stock,
                stock_replenished, category_created, product_category_changed
    Bulk Events: bulk_products_imported, bulk_inventory_updated,
                bulk_prices_updated, products_exported
    Error Events: product_sync_failed, inventory_sync_failed
"""

from .event_consumers import (
    BulkOperationHandler,
    OrderCreatedHandler,
    OrderFulfilledHandler,
    ProductEventConsumer,
)
from .event_producers import ProductEventProducer

__all__ = [
    # Producers
    "ProductEventProducer",
    # Consumer handlers
    "OrderCreatedHandler",
    "OrderFulfilledHandler",
    "BulkOperationHandler",
    # Consumer management
    "ProductEventConsumer",
]
