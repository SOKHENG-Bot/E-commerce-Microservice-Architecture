from datetime import datetime, timezone
from typing import Any, Dict, Optional

from user_service.app.core.settings import get_settings
from user_service.app.events.base import BaseEvent
from user_service.app.events.base.kafka_client import KafkaEventPublisher
from user_service.app.events.schemas.events import (
    PROFILE_CREATED,
    PROFILE_UPDATED,
    USER_CREATED,
    USER_DELETED,
    USER_EMAIL_VERIFICATION_REQUESTED,
    USER_EMAIL_VERIFIED,
    USER_UPDATED,
    ProfileCreatedEventData,
    ProfileUpdatedEventData,
    UserCreatedEventData,
    UserDeletedEventData,
    UserEmailVerificationRequestedEventData,
    UserEmailVerifiedEventData,
    UserUpdatedEventData,
)
from user_service.app.models.user import User

from ..utils.logging import setup_user_logging as setup_logging

settings = get_settings()
logger = setup_logging("user-producer-events", log_level=settings.LOG_LEVEL)


class UserEventProducer:
    """
    User service event producer using new BaseEvent pattern with proper schemas.
    All methods now use the corrected event creation pattern.
    """

    def __init__(self, event_publisher: KafkaEventPublisher):
        self.event_publisher = event_publisher

    # ==============================================
    # AUTHENTICATION EVENTS
    # ==============================================

    async def publish_user_created(self, user: User) -> None:
        """Publish user creation event"""
        try:
            # Create event data using our schema
            event_data = UserCreatedEventData(
                user_id=user.id,
                email=user.email,
                username=user.username or "",
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
                first_name=None,  # Will be filled from profile if exists
                last_name=None,  # Will be filled from profile if exists
                phone_number=user.phone_number,
            )

            # Create BaseEvent with our data
            event = BaseEvent(
                event_type=USER_CREATED,
                source_service="user-service",
                data=event_data.to_dict(),
            )

            # Publish using shared Kafka client
            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published user created event.",
                extra={
                    "user_id": str(user.id),
                    "email": user.email,
                },
            )
        except Exception as e:
            logger.error(f"Failed to publish user created event: {e}")
            # Don't fail registration if event publishing fails
            pass

    async def publish_verify_email(self, user: User):
        """Publish email verification event"""
        try:
            # Create event data
            event_data = UserEmailVerifiedEventData(
                user_id=user.id,
                email=user.email,
                verified_at=datetime.now(timezone.utc),
            )

            # Create BaseEvent
            event = BaseEvent(
                event_type=USER_EMAIL_VERIFIED,
                source_service="user-service",
                data=event_data.to_dict(),
            )

            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published verify email event.",
                extra={
                    "user_id": str(user.id),
                    "email": user.email,
                },
            )
        except Exception as e:
            logger.error(f"Failed to publish verify email event: {e}")
            raise

    async def publish_email_verification_request(
        self,
        user: User,
        verification_token: str,
        expires_in_minutes: int,
    ) -> None:
        """Publish email verification request event"""
        try:
            # Create event data
            event_data = UserEmailVerificationRequestedEventData(
                user_id=user.id,
                email=user.email,
                verification_token=verification_token,
                expires_in_minutes=expires_in_minutes,
                requested_at=datetime.now(timezone.utc),
            )

            # Create BaseEvent
            event = BaseEvent(
                event_type=USER_EMAIL_VERIFICATION_REQUESTED,
                source_service="user-service",
                data=event_data.to_dict(),
            )

            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published email verification request event.",
                extra={
                    "user_id": str(user.id),
                    "email": user.email,
                },
            )
        except Exception as e:
            logger.error(f"Failed to publish email verification request event: {e}")
            raise

    async def publish_password_reset_request(
        self,
        user: User,
        reset_token: str,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish password reset request event"""
        try:
            # Create event data
            event_data = UserUpdatedEventData(
                user_id=user.id,
                email=user.email,
                username=user.username or "",
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

            # Create BaseEvent for password reset request
            event = BaseEvent(
                event_type="user.password_reset_requested",
                source_service="user-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            # Add additional password reset data
            event.data.update(
                {
                    "reset_token": reset_token,
                    "requested_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published password reset request event.",
                extra={"user_id": str(user.id), "email": user.email},
            )
        except Exception as e:
            logger.error(f"Failed to publish password reset request event: {e}")
            raise

    async def publish_password_reset_confirm(
        self,
        user: User,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish password reset confirmation event"""
        try:
            event_data = UserUpdatedEventData(
                user_id=user.id,
                email=user.email,
                username=user.username or "",
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

            event = BaseEvent(
                event_type="user.password_reset_confirmed",
                source_service="user-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            event.data.update(
                {
                    "confirmed_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published password reset confirm event.",
                extra={"user_id": str(user.id), "email": user.email},
            )
        except Exception as e:
            logger.error(f"Failed to publish password reset confirm event: {e}")
            raise

    async def publish_logout(
        self,
        user: User,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish user logout event"""
        try:
            event_data = UserUpdatedEventData(
                user_id=user.id,
                email=user.email,
                username=user.username or "",
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

            event = BaseEvent(
                event_type="user.logged_out",
                source_service="user-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            event.data.update(
                {
                    "logout_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published logout event.",
                extra={"user_id": str(user.id), "email": user.email},
            )
        except Exception as e:
            logger.error(f"Failed to publish logout event: {e}")
            raise

    async def publish_user_login(
        self, user: User, login_ip: str, correlation_id: Optional[int] = None
    ) -> None:
        """Publish user login event"""
        try:
            event_data = UserUpdatedEventData(
                user_id=user.id,
                email=user.email,
                username=user.username or "",
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

            event = BaseEvent(
                event_type="user.logged_in",
                source_service="user-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            event.data.update(
                {
                    "login_ip": login_ip,
                    "login_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published user login event.",
                extra={
                    "user_id": str(user.id),
                    "email": user.email,
                    "login_ip": login_ip,
                },
            )
        except Exception as e:
            logger.error(f"Failed to publish user login event: {e}")
            raise

    # ==============================================
    # USER STATUS EVENTS
    # ==============================================

    async def publish_user_deactivated(
        self,
        user: User,
        reason: Optional[str] = None,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish user deactivation event"""
        try:
            event_data = UserUpdatedEventData(
                user_id=user.id,
                email=user.email,
                username=user.username or "",
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

            event = BaseEvent(
                event_type="user.deactivated",
                source_service="user-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            event.data.update(
                {
                    "deactivated_at": datetime.now(timezone.utc).isoformat(),
                    "reason": reason or "User requested",
                }
            )

            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published user deactivated event.",
                extra={"user_id": str(user.id), "email": user.email, "reason": reason},
            )
        except Exception as e:
            logger.error(f"Failed to publish user deactivated event: {e}")
            raise

    async def publish_user_reactivated(
        self,
        user: User,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish user reactivation event"""
        try:
            event_data = UserUpdatedEventData(
                user_id=user.id,
                email=user.email,
                username=user.username or "",
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

            event = BaseEvent(
                event_type="user.reactivated",
                source_service="user-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            event.data.update(
                {
                    "reactivated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published user reactivated event.",
                extra={"user_id": str(user.id), "email": user.email},
            )
        except Exception as e:
            logger.error(f"Failed to publish user reactivated event: {e}")
            raise

    # ==============================================
    # PROFILE EVENTS
    # ==============================================

    async def publish_profile_created(
        self,
        profile_data: Dict[str, Any],
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish profile creation event"""
        try:
            event_data = ProfileCreatedEventData(
                profile_id=profile_data["id"],
                user_id=profile_data["user_id"],
                first_name=profile_data.get("first_name"),
                last_name=profile_data.get("last_name"),
                date_of_birth=profile_data.get("date_of_birth"),
                created_at=profile_data["created_at"],
            )

            event = BaseEvent(
                event_type=PROFILE_CREATED,
                source_service="user-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published profile created event.",
                extra={
                    "profile_id": str(profile_data["id"]),
                    "user_id": str(profile_data["user_id"]),
                },
            )
        except Exception as e:
            logger.error(f"Failed to publish profile created event: {e}")
            raise

    async def publish_profile_updated(
        self,
        profile_data: Dict[str, Any],
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish profile update event"""
        try:
            event_data = ProfileUpdatedEventData(
                profile_id=profile_data["id"],
                user_id=profile_data["user_id"],
                first_name=profile_data.get("first_name"),
                last_name=profile_data.get("last_name"),
                date_of_birth=profile_data.get("date_of_birth"),
                updated_at=profile_data["updated_at"],
            )

            event = BaseEvent(
                event_type=PROFILE_UPDATED,
                source_service="user-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published profile updated event.",
                extra={
                    "profile_id": str(profile_data["id"]),
                    "user_id": str(profile_data["user_id"]),
                },
            )
        except Exception as e:
            logger.error(f"Failed to publish profile updated event: {e}")
            raise

    async def publish_avatar_updated(
        self,
        user: User,
        avatar_url: str,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish avatar update event"""
        try:
            event_data = UserUpdatedEventData(
                user_id=user.id,
                email=user.email,
                username=user.username or "",
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

            event = BaseEvent(
                event_type="user.avatar_updated",
                source_service="user-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            event.data.update(
                {
                    "avatar_url": avatar_url,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published avatar updated event.",
                extra={"user_id": str(user.id), "avatar_url": avatar_url},
            )
        except Exception as e:
            logger.error(f"Failed to publish avatar updated event: {e}")
            raise

    # ==============================================
    # ADDRESS EVENTS
    # ==============================================

    async def publish_address_created(
        self,
        user: User,
        address_data: Dict[str, Any],
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish address creation event"""
        try:
            event_data = UserUpdatedEventData(
                user_id=user.id,
                email=user.email,
                username=user.username or "",
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

            event = BaseEvent(
                event_type="user.address_created",
                source_service="user-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            event.data.update(
                {
                    "address_id": address_data["id"],
                    "address_type": address_data["type"],
                    "is_default": address_data.get("is_default", False),
                }
            )

            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published address created event.",
                extra={"user_id": str(user.id), "address_id": str(address_data["id"])},
            )
        except Exception as e:
            logger.error(f"Failed to publish address created event: {e}")
            raise

    async def publish_address_updated(
        self,
        user: User,
        address_data: Dict[str, Any],
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish address update event"""
        try:
            event_data = UserUpdatedEventData(
                user_id=user.id,
                email=user.email,
                username=user.username or "",
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

            event = BaseEvent(
                event_type="user.address_updated",
                source_service="user-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            event.data.update(
                {
                    "address_id": address_data["id"],
                    "address_type": address_data["type"],
                    "is_default": address_data.get("is_default", False),
                }
            )

            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published address updated event.",
                extra={"user_id": str(user.id), "address_id": str(address_data["id"])},
            )
        except Exception as e:
            logger.error(f"Failed to publish address updated event: {e}")
            raise

    async def publish_address_deleted(
        self,
        user: User,
        address_id: int,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish address deletion event"""
        try:
            event_data = UserUpdatedEventData(
                user_id=user.id,
                email=user.email,
                username=user.username or "",
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

            event = BaseEvent(
                event_type="user.address_deleted",
                source_service="user-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            event.data.update(
                {
                    "address_id": address_id,
                    "deleted_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published address deleted event.",
                extra={"user_id": str(user.id), "address_id": str(address_id)},
            )
        except Exception as e:
            logger.error(f"Failed to publish address deleted event: {e}")
            raise

    async def publish_default_address_changed(
        self,
        user: User,
        new_default_address_id: int,
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish default address change event"""
        try:
            event_data = UserUpdatedEventData(
                user_id=user.id,
                email=user.email,
                username=user.username or "",
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

            event = BaseEvent(
                event_type="user.default_address_changed",
                source_service="user-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            event.data.update(
                {
                    "new_default_address_id": new_default_address_id,
                    "changed_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published default address changed event.",
                extra={
                    "user_id": str(user.id),
                    "new_default_address_id": str(new_default_address_id),
                },
            )
        except Exception as e:
            logger.error(f"Failed to publish default address changed event: {e}")
            raise

    # ==============================================
    # GENERAL USER EVENTS
    # ==============================================

    async def publish_user_updated(
        self,
        user: User,
        updated_fields: Dict[str, Any],
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish general user update event"""
        try:
            event_data = UserUpdatedEventData(
                user_id=user.id,
                email=user.email,
                username=user.username or "",
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

            event = BaseEvent(
                event_type=USER_UPDATED,
                source_service="user-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            event.data.update(
                {
                    "updated_fields": updated_fields,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published user updated event.",
                extra={
                    "user_id": str(user.id),
                    "updated_fields": list(updated_fields.keys()),
                },
            )
        except Exception as e:
            logger.error(f"Failed to publish user updated event: {e}")
            raise

    async def publish_user_deleted(
        self,
        user_id: int,
        user_email: str,
        user_data: Dict[str, Any],
        correlation_id: Optional[int] = None,
    ) -> None:
        """Publish user deletion event"""
        try:
            # Create event data
            event_data = UserDeletedEventData(
                user_id=user_id,
                email=user_email,
                username=user_data.get("username", ""),
                deleted_at=datetime.now(timezone.utc),
            )

            # Create BaseEvent
            event = BaseEvent(
                event_type=USER_DELETED,
                source_service="user-service",
                correlation_id=correlation_id,
                data=event_data.to_dict(),
            )

            # Add deletion metadata
            event.data.update(
                {
                    "deletion_reason": user_data.get(
                        "deletion_reason", "user_requested"
                    ),
                    "soft_delete": user_data.get("soft_delete", False),
                }
            )

            await self.event_publisher.publish(event, topic="user.events")
            logger.info(
                "Published user deleted event.",
                extra={"user_id": str(user_id), "email": user_email},
            )
        except Exception as e:
            logger.error(f"Failed to publish user deleted event: {e}")
            raise
