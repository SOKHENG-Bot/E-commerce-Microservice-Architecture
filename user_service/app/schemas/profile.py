from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from user_service.app.models.profile import GenderEnum


class ProfileBase(BaseModel):
    avatar_url: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[GenderEnum] = None
    bio: Optional[str] = None
    preferences: Optional[dict[str, Any]] = {}


class ProfileCreate(ProfileBase):
    user_id: Optional[int] = None  # Required for bulk operations


class ProfileUpdate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Request/Response Models
class ProfileCompletenessResponse(BaseModel):
    completeness: int
    total_fields: int
    completed_fields: int


class MessageResponse(BaseModel):
    message: str
