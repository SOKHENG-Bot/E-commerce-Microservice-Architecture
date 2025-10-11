"""
Notification Service Event Management
Initializes and manages Kafka event publishing for the notification service.
"""

import logging
from typing import Optional

from ..events.base.kafka_client import KafkaEventPublisher
from ..events.producers import NotificationEventProducer
from .settings import get_settings

logger = logging.getLogger(__name__)

# Global instances
_kafka_publisher: Optional[KafkaEventPublisher] = None
_notification_event_producer: Optional[NotificationEventProducer] = None


async def init_events() -> None:
    """Initialize event publishing infrastructure"""
    global _kafka_publisher, _notification_event_producer

    try:
        settings = get_settings()

        # Initialize Kafka publisher with faster failure
        _kafka_publisher = KafkaEventPublisher(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            client_id=f"{settings.SERVICE_NAME}-producer",
            max_retries=3,  # Reduced from 20 to 3 for faster startup
            retry_delay=1.0,  # Reduced from 2.0 to 1.0
            enable_graceful_degradation=True,
        )

        # Start Kafka connection (non-blocking for startup)
        try:
            await _kafka_publisher.start(timeout=5.0)  # Reduced timeout
        except Exception as e:
            logger.warning(
                f"Kafka publisher start failed, continuing in degraded mode: {e}"
            )
            # Continue anyway - the publisher will work when Kafka becomes available

        # Initialize notification event producer
        _notification_event_producer = NotificationEventProducer(_kafka_publisher)

        logger.info("✅ Event publishing infrastructure initialized successfully")

    except Exception as e:
        logger.warning(f"Event publishing initialization failed: {e}")
        logger.info("Service will continue without event publishing (degraded mode)")


async def close_events() -> None:
    """Close event publishing infrastructure"""
    global _kafka_publisher, _notification_event_producer

    try:
        if _kafka_publisher:
            await _kafka_publisher.stop()
            logger.info("Event publishing infrastructure closed")
    except Exception as e:
        logger.error(f"Error closing event infrastructure: {e}")
    finally:
        _kafka_publisher = None
        _notification_event_producer = None


def get_event_producer() -> Optional[NotificationEventProducer]:
    """Get the notification event producer instance"""
    return _notification_event_producer


def get_notification_event_producer() -> Optional[NotificationEventProducer]:
    """Get the notification event producer instance (alias for compatibility)"""
    return _notification_event_producer


async def health_check_events() -> bool:
    """Check if event publishing is healthy"""
    if _kafka_publisher:
        return await _kafka_publisher.health_check()
    return False
