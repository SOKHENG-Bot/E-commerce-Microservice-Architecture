"""
Order Service Event Sourcing and CQRS (Command Query Responsibility Segregation) patterns
base classes and interfaces.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class BaseEvent(BaseModel):
    """Base class for all domain events"""

    event_id: str = uuid.uuid4().hex
    event_type: str
    timestamp: datetime = datetime.now(timezone.utc)
    version: str = "1.0"
    source_service: str = "order-service"
    correlation_id: Optional[int] = None
    data: Dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class EventHandler(ABC):
    """Abstract base class for event handlers"""

    @abstractmethod
    async def handle(self, event: BaseEvent) -> None:
        """Handle the event"""
        pass


class EventPublisher(ABC):
    """Abstract base class for event publishers"""

    @abstractmethod
    async def publish(self, event: BaseEvent) -> None:
        """Publish an event"""
        pass


class EventSubscriber(ABC):
    """Abstract base class for event subscribers"""

    @abstractmethod
    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to an event type"""
        pass
