"""
Order Service Event Management
Initializes and manages Kafka event publishing for the order service.
"""

import logging
from typing import Optional

from ..events.base.kafka_client import KafkaEventPublisher
from ..events.producers import OrderEventProducer
from .setting import get_settings

logger = logging.getLogger(__name__)

# Global instances
_kafka_publisher: Optional[KafkaEventPublisher] = None
_order_event_producer: Optional[OrderEventProducer] = None


async def init_events() -> None:
    """Initialize event publishing infrastructure"""
    global _kafka_publisher, _order_event_producer

    try:
        settings = get_settings()

        # Initialize Kafka publisher
        _kafka_publisher = KafkaEventPublisher(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            client_id=f"{settings.SERVICE_NAME}-producer",
            max_retries=10,
            retry_delay=2.0,
            enable_graceful_degradation=True,
        )

        # Start Kafka connection
        await _kafka_publisher.start(timeout=30.0)

        # Initialize order event producer
        _order_event_producer = OrderEventProducer(_kafka_publisher)

        logger.info("✅ Event publishing infrastructure initialized successfully")

    except Exception as e:
        logger.warning(f"⚠️ Event publishing initialization failed: {e}")
        logger.info("Service will continue without event publishing (degraded mode)")


async def close_events() -> None:
    """Close event publishing infrastructure"""
    global _kafka_publisher, _order_event_producer

    try:
        if _kafka_publisher:
            await _kafka_publisher.stop()
            logger.info("Event publishing infrastructure closed")
    except Exception as e:
        logger.error(f"Error closing event infrastructure: {e}")
    finally:
        _kafka_publisher = None
        _order_event_producer = None


def get_event_producer() -> Optional[OrderEventProducer]:
    """Get the order event producer instance"""
    return _order_event_producer


async def health_check_events() -> bool:
    """Check if event publishing is healthy"""
    if _kafka_publisher:
        return await _kafka_publisher.health_check()
    return False
