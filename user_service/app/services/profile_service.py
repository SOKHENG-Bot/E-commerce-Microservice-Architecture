from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.app.core.settings import get_settings
from user_service.app.events.event_producers import UserEventProducer
from user_service.app.models.profile import Profile
from user_service.app.repository.profile_repository import ProfileRepository
from user_service.app.schemas.user import (
    CurrentUserRequest,
    UserUpdateProfileRequest,
)

from ..utils.logging import setup_user_logging as setup_logging

settings = get_settings()
logger = setup_logging("profile_service", log_level=settings.LOG_LEVEL)


class ProfileService:
    def __init__(
        self, session: AsyncSession, event_publisher: Optional[UserEventProducer]
    ):
        self.session = session
        self.event_publisher = event_publisher
        self.profile_repository = ProfileRepository(session)

    async def user_get_profile(self, current_user: CurrentUserRequest) -> Profile:
        """Retrieve user profile"""

        try:
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User is not authenticated.",
                )
            user_int_id = int(current_user.user_id)
            profile = await self.profile_repository.get_profile(user_int_id)
            if not profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Profile not found.",
                )
            return profile

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Failed to retrieve user profile",
                extra={
                    "user_id": current_user.user_id,
                    "error_message": str(e),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve profile.",
            )

    async def user_update_profile(
        self, current_user: CurrentUserRequest, data: UserUpdateProfileRequest
    ) -> Profile:
        """Update user profile"""

        try:
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User is not authenticated.",
                )

            user_int_id = int(current_user.user_id)
            profile = await self.profile_repository.get_profile(user_int_id)
            if not profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Profile not found.",
                )

            update_value = data.model_dump(exclude_unset=True)
            updated_fields: dict[str, Any] = {}
            for key, value in update_value.items():
                if hasattr(profile, key):
                    old_value = getattr(profile, key)
                    setattr(profile, key, value)
                    if old_value != value:
                        updated_fields[key] = {"old": old_value, "new": value}

            if not updated_fields:
                return profile  # No changes made

            updated_profile = await self.profile_repository.update(profile)

            logger.info(
                "Profile updated successfully.",
                extra={
                    "user_id": current_user.user_id,
                    "profile_id": str(updated_profile.id),
                    "updated_fields_count": len(updated_fields),
                },
            )
            return updated_profile

        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating profile for user {current_user.user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile.",
            )
