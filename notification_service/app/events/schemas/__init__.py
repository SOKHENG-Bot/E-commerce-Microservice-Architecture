from typing import Dict, Optional

from pydantic import BaseModel


class NotificationSentEventData(BaseModel):
    """Event data for notification sent events"""

    notification_id: str
    user_id: str
    notification_type: str  # email, sms, push
    recipient: str
    subject: Optional[str] = None
    content: str
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return self.dict()


class NotificationDeliveredEventData(BaseModel):
    """Event data for notification delivered events"""

    notification_id: str
    user_id: str
    notification_type: str
    recipient: str
    delivered_at: str
    delivery_provider: Optional[str] = None
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return self.dict()


class NotificationFailedEventData(BaseModel):
    """Event data for notification failed events"""

    notification_id: str
    user_id: str
    notification_type: str
    recipient: str
    error_message: str
    error_code: Optional[str] = None
    retry_count: int = 0
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return self.dict()


class NotificationRequestedEventData(BaseModel):
    """Event data for notification request events"""

    user_id: str
    notification_type: str
    recipient: str
    subject: Optional[str] = None
    content: str
    priority: str = "normal"  # low, normal, high, urgent
    template_id: Optional[str] = None
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return self.dict()


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
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return self.dict()


class SMSSentEventData(BaseModel):
    """Event data for SMS sent events"""

    notification_id: str
    user_id: str
    recipient: str
    content: str
    provider: str
    message_id: Optional[str] = None
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return self.dict()


class PushNotificationSentEventData(BaseModel):
    """Event data for push notification sent events"""

    notification_id: str
    user_id: str
    device_token: str
    title: str
    body: str
    data: Optional[Dict] = None
    badge: Optional[int] = None
    sound: Optional[str] = None
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return self.dict()
