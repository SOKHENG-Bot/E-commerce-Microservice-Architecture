import asyncio
import json
from typing import Dict, List

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer  # type: ignore
from aiokafka.admin import AIOKafkaAdminClient, NewTopic  # type: ignore
from aiokafka.errors import KafkaConnectionError, KafkaError  # type: ignore

from ...core.setting import get_settings
from ...utils.logging import setup_product_logging as setup_logging
from . import BaseEvent, EventHandler, EventPublisher, EventSubscriber

logger = setup_logging(
    "product_service.events.kafka", log_level=get_settings().LOG_LEVEL
)


class KafkaEventPublisher(EventPublisher):
    """
    Product Service Kafka publisher with connection retry logic
    """

    def __init__(
        self,
        bootstrap_servers: str,
        client_id: str,
        max_retries: int = 20,
        retry_delay: float = 2.0,
        enable_graceful_degradation: bool = True,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_graceful_degradation = enable_graceful_degradation
        self.producer = None
        self.is_connected = False
        self._connection_lock = asyncio.Lock()

    async def ensure_topic_exists(self, topic_name: str):
        """Ensure a Kafka topic exists, creating it if necessary."""
        admin_client = AIOKafkaAdminClient(bootstrap_servers=self.bootstrap_servers)
        await admin_client.start()  # type: ignore
        try:
            topics = await admin_client.list_topics()
            if topic_name not in topics:
                await admin_client.create_topics(
                    [NewTopic(name=topic_name, num_partitions=1, replication_factor=1)]
                )
                logger.info(
                    "Created Kafka topic",
                    extra={"topic_name": topic_name, "operation": "create_topic"},
                )
        except Exception as e:
            logger.warning(
                "Error ensuring Kafka topic exists",
                extra={
                    "topic_name": topic_name,
                    "error": str(e),
                    "operation": "ensure_topic_exists",
                },
            )
        finally:
            await admin_client.close()  # type: ignore

    async def start(self, timeout: float = 30.0) -> None:
        """Start Kafka producer with retry logic"""
        async with self._connection_lock:
            if self.producer and self.is_connected:
                return

            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
                value_serializer=lambda x: json.dumps(x, default=str).encode("utf-8"),  # type: ignore
                key_serializer=lambda x: x.encode("utf-8") if x else None,  # type: ignore
                retry_backoff_ms=1000,
                request_timeout_ms=30000,
                connections_max_idle_ms=540000,
            )

            # Retry connection with exponential backoff
            for attempt in range(self.max_retries):
                try:
                    logger.info(
                        "Attempting Kafka connection",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": self.max_retries,
                            "operation": "kafka_connect",
                        },
                    )

                    # Use asyncio.wait_for to add timeout
                    await asyncio.wait_for(self.producer.start(), timeout=timeout)  # type: ignore

                    self.is_connected = True
                    logger.info("Successfully connected to Kafka")
                    return

                except (KafkaConnectionError, asyncio.TimeoutError) as e:  # noqa: F821
                    logger.warning(
                        f"Kafka connection attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {self.retry_delay * (2**attempt)} seconds..."
                    )

                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (2**attempt))
                    else:
                        logger.error(
                            f"Failed to connect to Kafka after {self.max_retries} attempts. "
                            f"Giving up. Running in degraded mode (events will be logged but not published)"
                        )
                        self.is_connected = False
                        return

    async def stop(self) -> None:
        """Stop Kafka producer"""
        async with self._connection_lock:
            if self.producer:
                try:
                    await self.producer.stop()  # type: ignore
                    logger.info("Kafka producer stopped")
                except Exception as e:
                    logger.warning(
                        "Error stopping Kafka producer",
                        extra={"error": str(e), "operation": "stop_producer"},
                    )
                finally:
                    self.producer = None
                    self.is_connected = False

    async def publish(self, event: BaseEvent, topic: str = None) -> None:  # type: ignore
        """Publish event with fallback handling"""
        if not self.is_connected or not self.producer:
            if self.enable_graceful_degradation:
                logger.warning(
                    f"Kafka not available, logging event instead: {event.event_type}",
                    extra={
                        "event_id": str(event.event_id),
                        "event_type": event.event_type,
                        "event_data": event.dict(),  # type: ignore
                    },
                )
                return
            else:
                raise KafkaConnectionError("Kafka producer not connected")

        if not topic:
            topic = self._get_topic_for_event(event.event_type)

        # Ensure topic exists before publishing
        await self.ensure_topic_exists(topic)

        partition_key = str(event.correlation_id) if event.correlation_id else None

        try:
            await self.producer.send_and_wait(  # type: ignore
                topic=topic,
                value=event.dict(),  # type: ignore
                key=partition_key,  # type: ignore
            )
            logger.info(
                "Published event to Kafka topic",
                extra={
                    "event_type": event.event_type,
                    "topic": topic,
                    "event_id": str(event.event_id),
                    "correlation_id": str(event.correlation_id)
                    if event.correlation_id
                    else None,
                    "operation": "publish_event",
                },
            )

        except KafkaError as e:
            if self.enable_graceful_degradation:
                logger.error(
                    f"Failed to publish event {event.event_type}, logging instead: {e}",
                    extra={
                        "event_id": str(event.event_id),
                        "event_type": event.event_type,
                        "event_data": event.dict(),  # type: ignore
                    },
                )
            else:
                logger.error(
                    "Failed to publish event to Kafka",
                    extra={
                        "event_type": event.event_type,
                        "error": str(e),
                        "event_id": str(event.event_id),
                        "correlation_id": str(event.correlation_id)
                        if event.correlation_id
                        else None,
                        "operation": "publish_event_failed",
                    },
                )
                raise

    def _get_topic_for_event(self, event_type: str) -> str:
        """Map event type to Kafka topic"""
        topic_mapping = {
            "product.created": "product.events",
            "product.updated": "product.events",
            "product.deleted": "product.events",
            "inventory.updated": "inventory.events",
            "category.created": "category.events",
            "category.updated": "category.events",
            "review.created": "review.events",
            "review.updated": "review.events",
        }
        return topic_mapping.get(event_type, "product.events")

    async def health_check(self) -> bool:
        """Check if Kafka connection is healthy"""
        try:
            if not self.producer or not self.is_connected:
                return False

            # Try to get cluster metadata as health check
            metadata = await self.producer.client.fetch_metadata()  # type: ignore
            return len(metadata.brokers) > 0  # type: ignore

        except Exception as e:
            logger.warning(
                "Kafka health check failed",
                extra={"error": str(e), "operation": "health_check"},
            )
            return False


class KafkaEventSubscriber(EventSubscriber):
    """Product Service Kafka subscriber with connection retry logic"""

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        client_id: str,
        max_retries: int = 5,
        retry_delay: float = 2.0,
        enable_graceful_degradation: bool = True,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.client_id = client_id
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_graceful_degradation = enable_graceful_degradation
        self.consumers: Dict[str, AIOKafkaConsumer] = {}
        self.handlers: Dict[str, List[EventHandler]] = {}
        self.running = False
        self.is_connected = False

    async def start(self, timeout: float = 30.0):
        """Start event subscriber with retry logic"""
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    "Attempting Kafka subscriber connection",
                    extra={
                        "attempt": attempt + 1,
                        "max_retries": self.max_retries,
                        "operation": "subscriber_connect",
                    },
                )

                # Test connection by creating a temporary consumer
                test_consumer = AIOKafkaConsumer(
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=f"{self.group_id}-health-check",
                    client_id=f"{self.client_id}-health-check",
                )

                await asyncio.wait_for(test_consumer.start(), timeout=timeout)  # type: ignore
                await test_consumer.stop()  # type: ignore

                self.running = True
                self.is_connected = True
                logger.info("Kafka subscriber connected successfully")
                return

            except (KafkaConnectionError, asyncio.TimeoutError) as e:
                logger.warning(
                    f"Kafka subscriber connection attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {self.retry_delay * (2**attempt)} seconds..."
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                else:
                    if self.enable_graceful_degradation:
                        logger.error(
                            "Failed to connect Kafka subscriber after all retries. "
                            "Running in degraded mode (no event consumption)"
                        )
                        self.running = False
                        self.is_connected = False
                        return
                    else:
                        logger.error(
                            "Failed to connect Kafka subscriber after all retries"
                        )
                        raise KafkaConnectionError(
                            f"Could not connect to Kafka at {self.bootstrap_servers}"
                        )

    async def stop(self):
        """Stop all consumers"""
        self.running = False
        self.is_connected = False

        for topic, consumer in self.consumers.items():
            try:
                await consumer.stop()  # type: ignore
                logger.info(
                    "Stopped Kafka consumer for topic",
                    extra={"topic": topic, "operation": "stop_consumer"},
                )
            except Exception as e:
                logger.warning(
                    "Error stopping Kafka consumer",
                    extra={
                        "topic": topic,
                        "error": str(e),
                        "operation": "stop_consumer_error",
                    },
                )

        self.consumers.clear()
        logger.info("All Kafka consumers stopped")

    async def subscribe(  # type: ignore
        self, topic: str, event_type: str, handler: EventHandler
    ) -> None:
        """Subscribe to an event type with connection handling"""
        if not self.is_connected:
            logger.warning(f"Cannot subscribe to {event_type} - Kafka not connected")
            return

        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

        if topic not in self.consumers:
            try:
                consumer = AIOKafkaConsumer(
                    topic,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=self.group_id,
                    client_id=f"{self.client_id}-{topic}",
                    value_deserializer=lambda x: json.loads(x.decode("utf-8")),  # type: ignore
                    enable_auto_commit=True,
                    auto_offset_reset="earliest",
                )

                await consumer.start()  # type: ignore
                self.consumers[topic] = consumer

                # Start consuming messages for this topic
                asyncio.create_task(self._consume_messages(topic, consumer))
                logger.info(
                    "Subscribed to event type on Kafka topic",
                    extra={
                        "event_type": event_type,
                        "topic": topic,
                        "operation": "subscribe",
                    },
                )

            except Exception as e:
                logger.error(
                    "Failed to subscribe to Kafka topic",
                    extra={
                        "topic": topic,
                        "error": str(e),
                        "operation": "subscribe_failed",
                    },
                )
                if not self.enable_graceful_degradation:
                    raise

    async def _consume_messages(self, topic: str, consumer: AIOKafkaConsumer):
        """Consume messages from a specific topic with error handling"""
        try:
            async for message in consumer:  # type: ignore
                if not self.running:
                    break

                try:
                    event_data = message.value  # type: ignore
                    event_type = event_data.get("event_type")  # type: ignore

                    if (
                        event_type
                        and isinstance(event_type, str)
                        and event_type in self.handlers
                    ):
                        event = BaseEvent(**event_data)  # type: ignore

                        for handler in self.handlers[event_type]:
                            try:
                                await handler.handle(event)
                            except Exception as e:
                                logger.error(
                                    "Event handler error",
                                    extra={
                                        "event_type": event_type,
                                        "error": str(e),
                                        "event_id": str(event.event_id),
                                        "correlation_id": str(event.correlation_id)
                                        if event.correlation_id
                                        else None,
                                        "operation": "handler_error",
                                    },
                                )

                except Exception as e:
                    logger.error(
                        "Error processing Kafka message",
                        extra={
                            "topic": topic,
                            "error": str(e),
                            "operation": "process_message_error",
                        },
                    )

        except Exception as e:
            logger.error(
                "Kafka consumer error",
                extra={"topic": topic, "error": str(e), "operation": "consumer_error"},
            )
