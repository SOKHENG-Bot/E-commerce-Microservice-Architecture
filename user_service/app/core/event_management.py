from typing import Optional

from user_service.app.events.base.kafka_client import KafkaEventPublisher

from ..events.event_producers import UserEventProducer
from ..utils.logging import setup_user_logging as setup_logging
from .settings import get_settings

# Setup structured logging for event management
logger = setup_logging("user_service.events", log_level=get_settings().LOG_LEVEL)

# Global instances
_kafka_publisher: Optional[KafkaEventPublisher] = None
_user_event_producer: Optional[UserEventProducer] = None


async def init_events() -> None:
    """Initialize event publishing infrastructure"""

    global _kafka_publisher, _user_event_producer

    try:
        settings = get_settings()

        logger.info(
            "Initializing event publishing infrastructure",
            extra={
                "operation": "init_events",
                "kafka_servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                "service_name": settings.SERVICE_NAME,
                "service": "user_service",
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

        # Initialize user event producer
        _user_event_producer = UserEventProducer(_kafka_publisher)

        logger.info(
            "Event publishing infrastructure initialized successfully",
            extra={
                "operation": "init_events_complete",
                "kafka_client_id": f"{settings.SERVICE_NAME}-producer",
                "service": "user_service",
                "event_type": "event_infrastructure_ready",
            },
        )

    except Exception as e:
        logger.warning(
            "Event publishing initialization failed - operating in degraded mode",
            extra={
                "operation": "init_events_failed",
                "error": str(e),
                "service": "user_service",
                "event_type": "event_infrastructure_failed",
                "degraded_mode": True,
            },
        )


async def close_events() -> None:
    """Close event publishing infrastructure"""

    global _kafka_publisher, _user_event_producer

    try:
        if _kafka_publisher:
            logger.info(
                "Closing event publishing infrastructure",
                extra={
                    "operation": "close_events",
                    "service": "user_service",
                    "event_type": "event_infrastructure_shutdown",
                },
            )
            await _kafka_publisher.stop()
            logger.info(
                "Event publishing infrastructure closed successfully",
                extra={
                    "operation": "close_events_complete",
                    "service": "user_service",
                    "event_type": "event_infrastructure_shutdown_complete",
                },
            )
    except Exception as e:
        logger.error(
            "Error closing event infrastructure",
            extra={
                "operation": "close_events_error",
                "error": str(e),
                "service": "user_service",
                "event_type": "event_infrastructure_shutdown_error",
            },
        )
    finally:
        _kafka_publisher = None
        _user_event_producer = None


def get_event_producer() -> Optional[UserEventProducer]:
    """Get the user event producer instance"""

    return _user_event_producer


def get_user_event_producer() -> Optional[UserEventProducer]:
    """Get the user event producer instance (alias for compatibility)"""

    return _user_event_producer


async def health_check_events() -> bool:
    """Check if event publishing is healthy"""

    if _kafka_publisher:
        is_healthy = await _kafka_publisher.health_check()
        logger.debug(
            "Event infrastructure health check",
            extra={
                "operation": "health_check_events",
                "healthy": is_healthy,
                "service": "user_service",
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
            "service": "user_service",
            "event_type": "event_health_check",
        },
    )
    return False
