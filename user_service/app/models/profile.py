from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, TEXT, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import UserServiceBaseModel


class GenderEnum(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class Profile(UserServiceBaseModel):
    __tablename__ = "profiles"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False
    )

    avatar_url: Mapped[str] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    gender: Mapped[GenderEnum] = mapped_column(
        SQLEnum(GenderEnum, name="gender_enum"), nullable=True, default=None
    )
    bio: Mapped[str] = mapped_column(TEXT, nullable=True)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=True)

    # relationships
    user = relationship("User", back_populates="profile")
