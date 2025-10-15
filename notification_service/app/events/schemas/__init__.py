from typing import Any, Dict, Optional

from pydantic import BaseModel


class NotificationSentEventData(BaseModel):
    """Event data for notification sent events"""

    notification_id: str
    user_id: str
    notification_type: str  # email, sms, push
    recipient: str
    subject: Optional[str] = None
    content: str
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class NotificationDeliveredEventData(BaseModel):
    """Event data for notification delivered events"""

    notification_id: str
    user_id: str
    notification_type: str
    recipient: str
    delivered_at: str
    delivery_provider: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class NotificationFailedEventData(BaseModel):
    """Event data for notification failed events"""

    notification_id: str
    user_id: str
    notification_type: str
    recipient: str
    error_message: str
    error_code: Optional[str] = None
    retry_count: int = 0
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class NotificationRequestedEventData(BaseModel):
    """Event data for notification request events"""

    user_id: str
    notification_type: str
    recipient: str
    subject: Optional[str] = None
    content: str
    priority: str = "normal"  # low, normal, high, urgent
    template_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class EmailSentEventData(BaseModel):
    """Event data for email sent events"""

    notification_id: str
    user_id: str
    recipient: str
    subject: str
    content: str
    cc: Optional[list[str]] = None
    bcc: Optional[list[str]] = None
    attachments: Optional[list[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class SMSSentEventData(BaseModel):
    """Event data for SMS sent events"""

    notification_id: str
    user_id: str
    recipient: str
    content: str
    provider: str
    message_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class PushNotificationSentEventData(BaseModel):
    """Event data for push notification sent events"""

    notification_id: str
    user_id: str
    device_token: str
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None
    badge: Optional[int] = None
    sound: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class EmailClickedEventData(BaseModel):
    """Event data for email clicked events"""

    notification_id: str
    user_id: str
    link_url: str
    clicked_at: str
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class NotificationPreferencesUpdatedEventData(BaseModel):
    """Event data for notification preferences updated events"""

    user_id: str
    preferences: Dict[str, bool]
    updated_at: str
    updated_by: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class UserUnsubscribedEventData(BaseModel):
    """Event data for user unsubscribed events"""

    user_id: str
    notification_type: str
    channel: str
    unsubscribed_at: str
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
