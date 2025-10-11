"""
User Service - Core Functions Only
Business logic for essential user management operations
"""

import time
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.app.core.settings import get_settings
from user_service.app.events.event_producers import UserEventProducer
from user_service.app.models.user import User
from user_service.app.repository.user_repository import UserRepository
from user_service.app.schemas.user import UserUpdate

from ..utils.logging import setup_user_logging as setup_logging

settings = get_settings()
logger = setup_logging("user_service", log_level=settings.LOG_LEVEL)


class UserService:
    def __init__(
        self, session: AsyncSession, event_publisher: Optional[UserEventProducer]
    ):
        self.session = session
        self.event_publisher = event_publisher
        self.user_repository = UserRepository(session)

    async def get_current_user_profile(self, user_id: str) -> User:
        """Get current user profile information"""
        start_time = time.time()

        logger.info(
            "User profile retrieval started",
            extra={
                "user_id": user_id,
                "operation": "get_current_user_profile",
            },
        )

        try:
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized",
                )

            user_info = await self.user_repository.query_info(int(user_id))
            duration_ms = round((time.time() - start_time) * 1000, 2)

            logger.info(
                "User profile retrieved successfully",
                extra={
                    "user_id": user_id,
                    "duration_ms": duration_ms,
                    "operation": "get_current_user_profile",
                },
            )
            if not user_info:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )
            return user_info

        except HTTPException:
            raise
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                "Failed to retrieve user profile",
                extra={
                    "user_id": user_id,
                    "error_message": str(e),
                    "duration_ms": duration_ms,
                    "operation": "get_current_user_profile",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

    async def update_current_user_profile(self, user_id: str, data: UserUpdate) -> User:
        """Update current user profile"""
        try:
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized",
                )

            user = await self.user_repository.query_id(int(user_id))
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )

            # Update user fields
            update_value = data.model_dump(exclude_unset=True)
            for key, value in update_value.items():
                setattr(user, key, value)

            update_user = await self.user_repository.update(user)

            # Publish user update event
            if self.event_publisher:
                await self.event_publisher.publish_user_updated(
                    user=update_user, updated_fields=update_value
                )

            logger.info(f"User profile updated: {user_id}")
            return update_user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

    async def get_account_information(self, user_id: str) -> dict[str, Any]:
        """Get comprehensive account information"""
        try:
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User is not authenticated.",
                )

            user = await self.user_repository.query_id(int(user_id))
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found.",
                )

            # Get profile information if available
            profile: Optional[dict[str, Any]] = None
            if hasattr(user, "profile") and user.profile:
                profile = {
                    "id": user.profile.id,
                    "bio": user.profile.bio,
                    "avatar_url": user.profile.avatar_url,
                    "date_of_birth": user.profile.date_of_birth.isoformat()
                    if user.profile.date_of_birth
                    else None,
                    "gender": user.profile.gender,
                    "preferences": user.profile.preferences,
                }

            # Get addresses if available
            addresses: list[dict[str, Any]] = []
            if hasattr(user, "addresses") and user.addresses:
                addresses = [
                    {
                        "id": addr.id,
                        "street_address": addr.street_address,
                        "apartment": addr.apartment,
                        "city": addr.city,
                        "state": addr.state,
                        "country": addr.country,
                        "postal_code": addr.postal_code,
                        "is_default": addr.is_default,
                    }
                    for addr in user.addresses
                ]

            # Return comprehensive account information
            account_info: dict[str, Any] = {
                "user_id": user_id,
                "email": user.email,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "date_joined": user.date_joined.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "username": user.username,
                "phone": user.phone_number,
                "profile": profile,
                "addresses": addresses,
                "roles": [role.name for role in user.roles] if user.roles else [],
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
            }

            logger.info(f"Account information retrieved for user {user_id}")
            return account_info

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving account information: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve account information.",
            )

    async def deactivate_account(self, user_id: str) -> None:
        """Deactivate user account"""
        try:
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User is not authenticated.",
                )

            user = await self.user_repository.query_id(int(user_id))
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found.",
                )

            user.is_active = False
            await self.user_repository.update(user)

            # Publish account deactivation event
            if self.event_publisher:
                await self.event_publisher.publish_user_deactivated(user)

            logger.info(f"User account deactivated: {user_id}")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deactivating user account: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate account.",
            )

    async def reactivate_account(self, email: str) -> User:
        """Reactivate deactivated user account"""
        try:
            user = await self.user_repository.query_email(email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User with this email does not exist.",
                )

            if user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User account is already active.",
                )

            user.is_active = True
            reactivated_user = await self.user_repository.update(user)

            # Publish account reactivation event
            if self.event_publisher:
                await self.event_publisher.publish_user_reactivated(reactivated_user)

            logger.info(f"User account reactivated: {user.id}")
            return reactivated_user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reactivating user account: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reactivate account.",
            )
