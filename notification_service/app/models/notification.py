from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, TEXT, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import NotificationServiceBaseModel


class NotificationType(Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"


class NotificationPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Notification(NotificationServiceBaseModel):
    __tablename__ = "notifications"

    user_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Temporarily removed FK for testing
    type: Mapped[str] = mapped_column(String(50), nullable=False)

    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(TEXT, nullable=False)
    template_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    template_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=NotificationStatus.PENDING.value, nullable=False
    )
    priority: Mapped[str] = mapped_column(
        String(20), default=NotificationPriority.MEDIUM.value, nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_response: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
