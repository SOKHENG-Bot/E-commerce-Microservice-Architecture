from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NotificationType(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"


class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class NotificationBase(BaseModel):
    user_id: int = Field(..., gt=0, description="User ID")
    type: NotificationType = Field(..., description="Notification type")
    channel: str = Field(
        ..., min_length=1, max_length=50, description="Notification channel"
    )
    recipient: str = Field(
        ..., min_length=1, max_length=255, description="Recipient (email, phone, token)"
    )
    subject: Optional[str] = Field(
        None, max_length=255, description="Notification subject"
    )
    content: str = Field(..., min_length=1, description="Notification content")
    priority: NotificationPriority = Field(
        NotificationPriority.MEDIUM, description="Notification priority"
    )


class NotificationCreate(NotificationBase):
    template_id: Optional[str] = Field(None, max_length=100, description="Template ID")
    template_data: Optional[dict[str, Any]] = Field(
        default_factory=dict, description="Template data"
    )
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")

    @field_validator("recipient")
    @classmethod
    def validate_recipient(cls, v: str) -> str:
        """Basic recipient validation"""
        if not v or not v.strip():
            raise ValueError("Recipient cannot be empty")
        return v.strip()


class NotificationUpdate(BaseModel):
    status: Optional[NotificationStatus] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    failure_reason: Optional[str] = Field(None, max_length=255)
    retry_count: Optional[int] = Field(None, ge=0)
    provider_response: Optional[dict[str, Any]] = None


class NotificationResponse(NotificationBase):
    id: int
    status: NotificationStatus
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    provider_response: Optional[dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationList(BaseModel):
    notifications: list[NotificationResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int
