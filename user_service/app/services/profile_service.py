"""
Profile Service - Core Functions Only
Business logic for essential user profile management operations
"""

import time
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.app.core.settings import get_settings
from user_service.app.events.event_producers import UserEventProducer
from user_service.app.models.profile import Profile
from user_service.app.repository.profile_repository import ProfileRepository
from user_service.app.schemas.profile import ProfileCreate, ProfileUpdate

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

    async def get_profile(self, user_id: str) -> Optional[Profile]:
        """Get user profile by user ID"""
        start_time = time.time()

        logger.info(
            "Profile retrieval started",
            extra={
                "user_id": user_id,
                "operation": "get_profile",
            },
        )

        try:
            user_int_id = int(user_id)
            profile = await self.profile_repository.get_profile(user_int_id)
            duration_ms = round((time.time() - start_time) * 1000, 2)

            if profile:
                logger.info(
                    "Profile retrieved successfully",
                    extra={
                        "user_id": user_id,
                        "profile_id": str(profile.id),
                        "duration_ms": duration_ms,
                        "operation": "get_profile",
                    },
                )
            else:
                logger.info(
                    "Profile not found for user",
                    extra={
                        "user_id": user_id,
                        "duration_ms": duration_ms,
                        "operation": "get_profile",
                    },
                )

            return profile

        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                "Failed to retrieve user profile",
                extra={
                    "user_id": user_id,
                    "error_message": str(e),
                    "duration_ms": duration_ms,
                    "operation": "get_profile",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve profile.",
            )

    async def create_profile(self, user_id: str, data: ProfileCreate) -> Profile:
        """Create a new profile for a user"""
        try:
            user_int_id = int(user_id)
            # Check if profile already exists
            existing_profile = await self.profile_repository.get_profile(user_int_id)
            if existing_profile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Profile already exists for this user.",
                )

            # Create new profile
            profile = Profile(
                user_id=user_int_id,
                avatar_url=data.avatar_url,
                date_of_birth=data.date_of_birth,
                gender=data.gender,
                bio=data.bio,
                preferences=data.preferences or {},
            )

            created_profile = await self.profile_repository.create(profile)

            # Publish profile created event
            profile_data: Dict[str, Any] = {
                "avatar_url": created_profile.avatar_url,
                "date_of_birth": created_profile.date_of_birth.isoformat()
                if created_profile.date_of_birth
                else None,
                "gender": created_profile.gender.value
                if created_profile.gender
                else None,
                "bio": created_profile.bio,
                "preferences": created_profile.preferences or {},
            }
            if self.event_publisher:
                await self.event_publisher.publish_profile_created(
                    user_id=user_int_id,
                    profile_data=profile_data,
                )

            logger.info(
                "Profile created successfully.",
                extra={
                    "user_id": user_id,
                    "profile_id": str(created_profile.id),
                },
            )

            return created_profile

        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating profile for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create profile.",
            )

    async def update_profile(self, user_id: str, data: ProfileUpdate) -> Profile:
        """Update user profile"""
        try:
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User is not authenticated.",
                )

            user_int_id = int(user_id)
            profile = await self.profile_repository.get_profile(user_int_id)
            if not profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Profile not found.",
                )

            # Update profile fields
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
                    "user_id": user_id,
                    "profile_id": str(updated_profile.id),
                    "updated_fields_count": len(updated_fields),
                },
            )

            return updated_profile

        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating profile for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile.",
            )
