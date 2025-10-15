from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class UserEventData(BaseModel):
    """Base user event data structure"""

    user_id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for BaseEvent compatibility"""
        return self.model_dump()


class UserCreatedEventData(UserEventData):
    """Data for user creation events"""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None


class UserUpdatedEventData(UserEventData):
    """Data for user update events"""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    previous_email: Optional[str] = None


class UserDeletedEventData(BaseModel):
    """Data for user deletion events"""

    user_id: int
    email: str
    username: str
    deleted_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for BaseEvent compatibility"""
        return self.model_dump()


class UserEmailVerificationRequestedEventData(BaseModel):
    """Data for email verification request events"""

    user_id: int
    email: str
    verification_token: str
    expires_in_minutes: int
    requested_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for BaseEvent compatibility"""
        return self.model_dump()


class UserEmailVerifiedEventData(BaseModel):
    """Data for email verification events"""

    user_id: int
    email: str
    verified_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for BaseEvent compatibility"""
        return self.model_dump()


class ProfileCreatedEventData(BaseModel):
    """Data for profile creation events"""

    profile_id: int
    user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for BaseEvent compatibility"""
        return self.model_dump()


class ProfileUpdatedEventData(BaseModel):
    """Data for profile update events"""

    profile_id: int
    user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for BaseEvent compatibility"""
        return self.model_dump()


# Event type constants
USER_CREATED = "user.created"
USER_UPDATED = "user.updated"
USER_DELETED = "user.deleted"
USER_EMAIL_VERIFICATION_REQUESTED = "user.email_verification_requested"
USER_EMAIL_VERIFIED = "user.email_verified"
PROFILE_CREATED = "profile.created"
PROFILE_UPDATED = "profile.updated"
