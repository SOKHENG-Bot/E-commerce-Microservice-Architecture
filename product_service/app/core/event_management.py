"""
Product Service Event Management
Initializes and manages Kafka event publishing for the product service.
"""

from typing import Optional

from ..events.base.kafka_client import KafkaEventPublisher
from ..events.event_producers import ProductEventProducer
from ..utils.logging import setup_product_logging as setup_logging
from .setting import get_settings

# Setup structured logging for event management
logger = setup_logging("product_service.events", log_level=get_settings().LOG_LEVEL)

# Global instances
_kafka_publisher: Optional[KafkaEventPublisher] = None
_product_event_producer: Optional[ProductEventProducer] = None


async def init_events() -> None:
    """Initialize event publishing infrastructure"""
    global _kafka_publisher, _product_event_producer

    try:
        settings = get_settings()

        logger.info(
            "Initializing event publishing infrastructure",
            extra={
                "operation": "init_events",
                "kafka_servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                "service_name": settings.SERVICE_NAME,
                "service": "product_service",
                "event_type": "event_infrastructure_init",
            },
        )

        # Initialize Kafka publisher
        _kafka_publisher = KafkaEventPublisher(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            client_id=f"{settings.SERVICE_NAME}-producer",
            max_retries=20,
            retry_delay=2.0,
            enable_graceful_degradation=True,
        )

        # Start Kafka connection
        await _kafka_publisher.start(timeout=30.0)

        # Initialize product event producer
        _product_event_producer = ProductEventProducer(_kafka_publisher)

        logger.info(
            "Event publishing infrastructure initialized successfully",
            extra={
                "operation": "init_events_complete",
                "kafka_client_id": f"{settings.SERVICE_NAME}-producer",
                "service": "product_service",
                "event_type": "event_infrastructure_ready",
            },
        )

    except Exception as e:
        logger.warning(
            "Event publishing initialization failed - operating in degraded mode",
            extra={
                "operation": "init_events_failed",
                "error": str(e),
                "service": "product_service",
                "event_type": "event_infrastructure_failed",
                "degraded_mode": True,
            },
        )


async def close_events() -> None:
    """Close event publishing infrastructure"""
    global _kafka_publisher, _product_event_producer

    try:
        if _kafka_publisher:
            logger.info(
                "Closing event publishing infrastructure",
                extra={
                    "operation": "close_events",
                    "service": "product_service",
                    "event_type": "event_infrastructure_shutdown",
                },
            )
            await _kafka_publisher.stop()
            logger.info(
                "Event publishing infrastructure closed successfully",
                extra={
                    "operation": "close_events_complete",
                    "service": "product_service",
                    "event_type": "event_infrastructure_shutdown_complete",
                },
            )
    except Exception as e:
        logger.error(
            "Error closing event infrastructure",
            extra={
                "operation": "close_events_error",
                "error": str(e),
                "service": "product_service",
                "event_type": "event_infrastructure_shutdown_error",
            },
        )
    finally:
        _kafka_publisher = None
        _product_event_producer = None


def get_event_producer() -> Optional[ProductEventProducer]:
    """Get the product event producer instance"""
    logger.info(
        f"get_event_producer called, _product_event_producer is {_product_event_producer}",
        extra={
            "operation": "get_event_producer",
            "has_producer": _product_event_producer is not None,
        },
    )
    return _product_event_producer


def get_product_event_producer() -> Optional[ProductEventProducer]:
    """Get the product event producer instance (alias for compatibility)"""
    return _product_event_producer


async def health_check_events() -> bool:
    """Check if event publishing is healthy"""
    if _kafka_publisher:
        is_healthy = await _kafka_publisher.health_check()
        logger.debug(
            "Event infrastructure health check",
            extra={
                "operation": "health_check_events",
                "healthy": is_healthy,
                "service": "product_service",
                "event_type": "event_health_check",
            },
        )
        return is_healthy

    logger.debug(
        "Event infrastructure health check - no publisher available",
        extra={
            "operation": "health_check_events",
            "healthy": False,
            "publisher_available": False,
            "service": "product_service",
            "event_type": "event_health_check",
        },
    )
    return False
