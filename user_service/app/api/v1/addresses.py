from typing import Annotated, List

from fastapi import APIRouter, HTTPException, Path, status

from user_service.app.api.dependencies import (
    AddressServiceDep,
    CurrentUserIdDep,
)
from user_service.app.schemas.address import (
    AddressCreate,
    AddressResponse,
    AddressUpdate,
    MessageResponse,
)
from user_service.app.services.address_service import AddressService
from user_service.app.utils.logging import setup_user_logging

# Setup logger
logger = setup_user_logging("addresses")

# Router Configuration
address_router = APIRouter(prefix="/addresses")

# Dependencies
# Using global dependencies from dependencies.py


@address_router.get(
    "/user/{user_id}",
    response_model=List[AddressResponse],
    status_code=status.HTTP_200_OK,
)
async def get_user_addresses(
    user_id: Annotated[int, Path(..., description="User ID", gt=0, examples=[1])],
    current_user_id: str = CurrentUserIdDep,
    address_service: AddressService = AddressServiceDep,
):
    """Get all addresses for a specific user."""
    try:
        # Verify the user exists and is authorized
        current_user_int_id = int(current_user_id)
        if current_user_int_id != user_id:
            logger.warning(
                f"Unauthorized access attempt to user {user_id} addresses by user {current_user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own addresses",
            )

        # Mock empty addresses list for now
        addresses: List[AddressResponse] = []

        logger.info(f"Retrieved {len(addresses)} addresses for user {user_id}")
        return addresses

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve addresses for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve addresses",
        ) from e


@address_router.get(
    "/{address_id}",
    response_model=AddressResponse,
    status_code=status.HTTP_200_OK,
)
async def get_address(
    address_id: Annotated[int, Path(..., description="Address ID", gt=0, examples=[1])],
    current_user_id: str = CurrentUserIdDep,
    address_service: AddressService = AddressServiceDep,
):
    """Get a specific address by ID."""
    try:
        # Mock address for now - would call address_service.get_address_by_id(address_id)
        current_user_int_id = int(current_user_id)
        address = AddressResponse(
            id=address_id,
            user_id=current_user_int_id,
            street="Mock Street",
            city="Mock City",
            state="Mock State",
            zip_code="12345",
            country="Mock Country",
        )

        # Check if user owns the address or is admin
        if address.user_id != current_user_int_id:
            logger.warning(
                f"Unauthorized access attempt to address {address_id} by user {current_user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own addresses",
            )

        logger.info(f"Retrieved address {address_id} for user {current_user_id}")
        return address

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve address {address_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve address",
        ) from e


@address_router.post(
    "/",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_address(
    address_data: AddressCreate,
    current_user_id: str = CurrentUserIdDep,
    address_service: AddressService = AddressServiceDep,
):
    """Create a new address for the authenticated user."""
    try:
        # Mock address creation for now
        current_user_int_id = int(current_user_id)
        new_address = AddressResponse(
            id=1,
            user_id=current_user_int_id,
            street=getattr(address_data, "street", "Mock Street"),
            city=getattr(address_data, "city", "Mock City"),
            state=getattr(address_data, "state", "Mock State"),
            zip_code=getattr(address_data, "zip_code", "12345"),
            country=getattr(address_data, "country", "Mock Country"),
        )

        logger.info(f"Created address {new_address.id} for user {current_user_id}")
        return new_address

    except Exception as e:
        logger.error(f"Failed to create address for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create address",
        ) from e


@address_router.put(
    "/{address_id}",
    response_model=AddressResponse,
    status_code=status.HTTP_200_OK,
)
async def update_address(
    address_id: Annotated[int, Path(..., description="Address ID", gt=0, examples=[1])],
    address_data: AddressUpdate,
    current_user_id: str = CurrentUserIdDep,
    address_service: AddressService = AddressServiceDep,
):
    """Update an existing address."""
    try:
        # Mock address update for now
        current_user_int_id = int(current_user_id)
        updated_address = AddressResponse(
            id=address_id,
            user_id=current_user_int_id,
            street="Updated Street",
            city="Updated City",
            state="Updated State",
            zip_code="54321",
            country="Updated Country",
        )

        logger.info(f"Updated address {address_id} for user {current_user_id}")
        return updated_address

    except Exception as e:
        logger.error(f"Failed to update address {address_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update address",
        ) from e


@address_router.delete(
    "/{address_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_address(
    address_id: Annotated[int, Path(..., description="Address ID", gt=0, examples=[1])],
    current_user_id: str = CurrentUserIdDep,
    address_service: AddressService = AddressServiceDep,
):
    """Delete an address."""
    try:
        # Mock address deletion for now
        success = True

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete address",
            )

        logger.info(f"Deleted address {address_id} for user {current_user_id}")
        return MessageResponse(message="Address deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete address {address_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete address",
        ) from e
