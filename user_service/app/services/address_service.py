from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.app.core.settings import get_settings
from user_service.app.events.event_producers import UserEventProducer
from user_service.app.models.address import Address
from user_service.app.repository.address_repository import AddressRepository
from user_service.app.schemas.user import CurrentUserRequest, UserUpdateAddressesRequest

from ..utils.logging import setup_user_logging as setup_logging

settings = get_settings()
logger = setup_logging("address_service", log_level=settings.LOG_LEVEL)


class AddressService:
    def __init__(
        self, session: AsyncSession, event_publisher: Optional[UserEventProducer]
    ):
        self.session = session
        self.event_publisher = event_publisher
        self.address_repository = AddressRepository(session)

    async def user_get_address(self, current_user: CurrentUserRequest) -> Address:
        """Retrieve all addresses for a user"""

        try:
            if not current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User is not authenticated.",
                )
            address = await self.address_repository.get_address_by_id(
                current_user.user_id
            )
            if not address:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Address not found.",
                )
            return address
        except Exception as e:
            logger.error(
                "Failed to retrieve user addresses",
                extra={
                    "user_id": str(current_user.user_id),
                    "error_message": str(e),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve addresses.",
            )

    async def user_update_address(
        self, current_user: CurrentUserRequest, data: UserUpdateAddressesRequest
    ) -> Address:
        """Update user's address"""

        try:
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User is not authenticated.",
                )

            user_int_id = int(current_user.user_id)
            address = await self.address_repository.get_address_by_id(user_int_id)
            if not address:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Address not found.",
                )

            if data.address.is_default and data.address.type:
                await self.address_repository.unset_default_addresses(
                    user_int_id,
                    data.address.type,
                )

            update_value = data.model_dump(exclude_unset=True)
            updated_fields: dict[str, Any] = {}

            for key, value in update_value.items():
                if hasattr(address, key) and value is not None:
                    old_value = getattr(address, key)
                    setattr(address, key, value)
                    if old_value != value:
                        updated_fields[key] = {"old": old_value, "new": value}

            if not updated_fields:
                return address

            updated_address = await self.address_repository.update(address)

            if self.event_publisher:
                await self.event_publisher.publish_address_updated(
                    user_id=user_int_id,
                    address_id=address.id,
                    updated_fields=updated_fields,
                )

            logger.info(
                "Address updated successfully.",
                extra={
                    "user_id": user_int_id,
                    "address_id": str(address.id),
                    "updated_fields_count": len(updated_fields),
                },
            )

            return updated_address

        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating address: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update address.",
            )
