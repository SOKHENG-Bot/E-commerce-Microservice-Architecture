from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class BulkNotificationBase(BaseModel):
    user_ids: List[int] = Field(
        ..., min_length=1, max_length=10000, description="List of user IDs to notify"
    )
    notification_type: str = Field(
        ..., min_length=1, max_length=50, description="Type of notification"
    )
    channel: str = Field(
        ..., min_length=1, max_length=50, description="Notification channel"
    )
    subject: Optional[str] = Field(
        None, max_length=255, description="Notification subject"
    )
    content: str = Field(..., min_length=1, description="Notification content")
    template_id: Optional[str] = Field(
        None, max_length=100, description="Template ID to use"
    )
    template_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Template data"
    )
    priority: str = Field("medium", description="Notification priority")
    batch_size: Optional[int] = Field(
        50, ge=1, le=200, description="Batch size for processing"
    )
    max_concurrent: Optional[int] = Field(
        5, ge=1, le=20, description="Maximum concurrent batches"
    )

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        """Validate notification channel."""
        allowed_channels = ["email", "sms", "push"]
        if v not in allowed_channels:
            raise ValueError(f"Channel must be one of: {', '.join(allowed_channels)}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Validate notification priority."""
        allowed_priorities = ["low", "medium", "high"]
        if v not in allowed_priorities:
            raise ValueError(
                f"Priority must be one of: {', '.join(allowed_priorities)}"
            )
        return v


class BulkNotificationCreate(BulkNotificationBase):
    pass


class BulkNotificationResponse(BaseModel):
    job_id: str
    total_users: int
    total_sent: int
    total_failed: int
    success_rate: float
    processing_time_seconds: float
    batch_results: List[Dict[str, Any]]


class BatchResult(BaseModel):
    batch_index: int
    batch_size: int
    sent: int
    failed: int
    processing_time: float
    error: Optional[str] = None
