"""
Address Service - Core Functions Only
Business logic for essential address management operations
"""

import time
from typing import Any, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.app.core.settings import get_settings
from user_service.app.events.event_producers import UserEventProducer
from user_service.app.models.address import Address
from user_service.app.repository.address_repository import AddressRepository
from user_service.app.schemas.address import AddressCreate, AddressUpdate

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

    async def get_user_addresses(self, user_id: int) -> List[Address]:
        """Get all addresses for a user"""
        start_time = time.time()

        logger.info(
            "Address retrieval started",
            extra={
                "user_id": str(user_id),
                "operation": "get_user_addresses",
            },
        )

        try:
            addresses = await self.address_repository.get_addresses_by_user(user_id)
            duration_ms = round((time.time() - start_time) * 1000, 2)

            logger.info(
                "Addresses retrieved successfully",
                extra={
                    "user_id": str(user_id),
                    "address_count": len(addresses),
                    "duration_ms": duration_ms,
                    "operation": "get_user_addresses",
                },
            )
            return addresses

        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                "Failed to retrieve user addresses",
                extra={
                    "user_id": str(user_id),
                    "error_message": str(e),
                    "duration_ms": duration_ms,
                    "operation": "get_user_addresses",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve addresses.",
            )

    async def get_address_by_id(self, address_id: int, user_id: int) -> Address:
        """Get specific address by ID"""
        start_time = time.time()

        logger.info(
            "Address retrieval by ID started",
            extra={
                "address_id": str(address_id),
                "user_id": str(user_id),
                "operation": "get_address_by_id",
            },
        )

        try:
            address = await self.address_repository.get_address_by_id(address_id)
            duration_ms = round((time.time() - start_time) * 1000, 2)

            if not address:
                logger.warning(
                    "Address not found",
                    extra={
                        "address_id": str(address_id),
                        "user_id": str(user_id),
                        "duration_ms": duration_ms,
                        "operation": "get_address_by_id",
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Address not found.",
                )

            if address.user_id != user_id:
                logger.warning(
                    "Access denied to address",
                    extra={
                        "address_id": str(address_id),
                        "user_id": str(user_id),
                        "address_owner_id": str(address.user_id),
                        "duration_ms": duration_ms,
                        "operation": "get_address_by_id",
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this address.",
                )

            logger.info(
                "Address retrieved successfully by ID",
                extra={
                    "address_id": str(address_id),
                    "user_id": str(user_id),
                    "address_type": str(address.type),
                    "duration_ms": duration_ms,
                    "operation": "get_address_by_id",
                },
            )

            return address
        except HTTPException:
            raise
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                "Failed to retrieve address by ID",
                extra={
                    "address_id": str(address_id),
                    "user_id": str(user_id),
                    "error_message": str(e),
                    "duration_ms": duration_ms,
                    "operation": "get_address_by_id",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve address.",
            )

    async def create_address(self, user_id: str, data: AddressCreate) -> Address:
        """Create a new address for a user"""
        start_time = time.time()

        logger.info(
            "Address creation started",
            extra={
                "user_id": user_id,
                "address_type": str(data.type),
                "is_default": data.is_default,
                "city": data.city,
                "country": data.country,
                "operation": "create_address",
            },
        )

        try:
            user_int_id = int(user_id)
            # If this is set as default, unset other default addresses of the same type
            if data.is_default:
                await self.address_repository.unset_default_addresses(
                    user_int_id,
                    data.type,
                )
                logger.debug(
                    "Unset other default addresses of same type",
                    extra={
                        "user_id": user_id,
                        "address_type": str(data.type),
                    },
                )

            # Create new address
            address = Address(
                user_id=user_int_id,
                type=data.type,
                street_address=data.street_address,
                apartment=data.apartment,
                city=data.city,
                state=data.state,
                postal_code=data.postal_code,
                country=data.country,
                is_default=data.is_default,
            )

            created_address = await self.address_repository.create(address)

            # Publish address creation event
            if self.event_publisher:
                await self.event_publisher.publish_address_created(
                    user_id=user_int_id,
                    address_id=created_address.id,
                    address_data={
                        "street_address": data.street_address,
                        "apartment": data.apartment,
                        "city": data.city,
                        "state": data.state,
                        "postal_code": data.postal_code,
                        "country": data.country,
                        "address_type": data.type.value if data.type else None,
                        "is_default": data.is_default,
                    },
                )

            duration_ms = round((time.time() - start_time) * 1000, 2)

            logger.info(
                "Address created successfully",
                extra={
                    "user_id": user_id,
                    "address_id": str(created_address.id),
                    "address_type": str(data.type),
                    "is_default": data.is_default,
                    "duration_ms": duration_ms,
                    "operation": "create_address",
                },
            )

            return created_address

        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            duration_ms = round((time.time() - start_time) * 1000, 2)

            logger.error(
                "Failed to create address",
                extra={
                    "user_id": user_id,
                    "address_type": str(data.type),
                    "error_message": str(e),
                    "duration_ms": duration_ms,
                    "operation": "create_address",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create address.",
            )

    async def update_address(
        self, address_id: int, user_id: str, data: AddressUpdate
    ) -> Address:
        """Update an existing address"""
        try:
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User is not authenticated.",
                )

            user_int_id = int(user_id)
            address = await self.address_repository.get_address_by_id(address_id)
            if not address:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Address not found.",
                )

            if address.user_id != user_int_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this address.",
                )

            # If setting as default, unset other default addresses of the same type
            if data.is_default and data.type:
                await self.address_repository.unset_default_addresses(
                    user_int_id,
                    data.type,
                )
            elif data.is_default and not data.type:
                await self.address_repository.unset_default_addresses(
                    user_int_id,
                    address.type,
                )

            # Update address fields
            update_value = data.model_dump(exclude_unset=True)
            updated_fields: dict[str, Any] = {}

            for key, value in update_value.items():
                if hasattr(address, key) and value is not None:
                    old_value = getattr(address, key)
                    setattr(address, key, value)
                    if old_value != value:
                        updated_fields[key] = {"old": old_value, "new": value}

            if not updated_fields:
                return address  # No changes made

            updated_address = await self.address_repository.update(address)

            # Publish address update event
            if self.event_publisher:
                await self.event_publisher.publish_address_updated(
                    user_id=user_int_id,
                    address_id=address.id,
                    updated_fields=updated_fields,
                )

            logger.info(
                "Address updated successfully.",
                extra={
                    "user_id": user_id,
                    "address_id": str(address_id),
                    "updated_fields_count": len(updated_fields),
                },
            )

            return updated_address

        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating address {address_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update address.",
            )
