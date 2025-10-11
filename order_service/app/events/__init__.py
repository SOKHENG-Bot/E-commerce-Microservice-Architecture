"""
Events module for the Order Service.

This module contains event producers and consumers for handling
order-related events in the microservices architecture.

Producers:
    - OrderEventProducer: Publishes order lifecycle events
    - Order events: Create, status updates, cancellations, fulfillment, delivery
    - Payment events: Payment processing, failures, refunds
    - Cart events: Item additions, removals, cart clearing

Consumers:
    - PaymentProcessedHandler: Updates order status on successful payments
    - PaymentFailedHandler: Handles payment failures and order status updates
    - RefundProcessedHandler: Records refunds and updates order status
    - ProductUpdatedHandler: Handles product changes affecting orders
    - ProductDeletedHandler: Flags orders with deleted products
    - InventoryLowStockHandler: Alerts about potential fulfillment issues
    - InventoryOutOfStockHandler: Cancels orders for out-of-stock products
    - OrderEventConsumer: Manages event consumption and subscriptions

Event Types Supported:
    Core Events: order.created, order.status_updated, order.cancelled,
                order.fulfilled, order.delivered
    Payment Events: payment.processed, payment.failed, refund.processed
    Cart Events: cart.item_added, cart.item_removed, cart.cleared
    External Events: product.updated, product.deleted, inventory.low_stock,
                   inventory.out_of_stock
"""

from .consumers import (
    InventoryLowStockHandler,
    InventoryOutOfStockHandler,
    OrderEventConsumer,
    PaymentFailedHandler,
    PaymentProcessedHandler,
    ProductDeletedHandler,
    ProductUpdatedHandler,
    RefundProcessedHandler,
    get_order_event_consumer,
    shutdown_order_event_consumer,
)
from .producers import OrderEventProducer

__all__ = [
    # Producers
    "OrderEventProducer",
    # Consumer handlers
    "PaymentProcessedHandler",
    "PaymentFailedHandler",
    "RefundProcessedHandler",
    "ProductUpdatedHandler",
    "ProductDeletedHandler",
    "InventoryLowStockHandler",
    "InventoryOutOfStockHandler",
    # Consumer management
    "OrderEventConsumer",
    "get_order_event_consumer",
    "shutdown_order_event_consumer",
]
