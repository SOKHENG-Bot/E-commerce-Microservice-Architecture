"""
User Service Event Schemas
==========================

Event data schemas specific to the user service domain.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel

# ==============================================
# USER EVENT DATA SCHEMAS
# ==============================================


class UserCreatedEventData(BaseModel):
    """Data schema for user creation events"""

    user_id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class UserUpdatedEventData(BaseModel):
    """Data schema for user update events"""

    user_id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class UserEmailVerifiedEventData(BaseModel):
    """Data schema for email verification events"""

    user_id: int
    email: str
    verified_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class UserDeletedEventData(BaseModel):
    """Data schema for user deletion events"""

    user_id: int
    email: str
    username: str
    deleted_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ProfileCreatedEventData(BaseModel):
    """Data schema for profile creation events"""

    profile_id: int
    user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ProfileUpdatedEventData(BaseModel):
    """Data schema for profile update events"""

    profile_id: int
    user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


# ==============================================
# EVENT TYPE CONSTANTS
# ==============================================

USER_CREATED = "user.created"
USER_UPDATED = "user.updated"
USER_DELETED = "user.deleted"
USER_EMAIL_VERIFIED = "user.email_verified"
PROFILE_CREATED = "profile.created"
PROFILE_UPDATED = "profile.updated"
