from typing import Optional

from fastapi import APIRouter, HTTPException, status

from user_service.app.api.dependencies import (
    AddressServiceDep,
    CurrentUserIdDep,
)
from user_service.app.schemas.user import (
    AddressResponse,
    CurrentUserRequest,
    UserGetAddressesResponse,
    UserUpdateAddressesRequest,
    UserUpdateAddressesResponse,
)
from user_service.app.services.address_service import AddressService
from user_service.app.utils.logging import setup_user_logging

logger = setup_user_logging("addresses")
address_router = APIRouter(prefix="/addresses")


@address_router.get(
    "/",
    response_model=UserGetAddressesResponse,
    status_code=status.HTTP_200_OK,
)
async def user_get_addresses(
    current_user: str = CurrentUserIdDep,
    service: AddressService = AddressServiceDep,
    correlation_id: Optional[str] = None,
) -> UserGetAddressesResponse:
    try:
        user = CurrentUserRequest(user_id=int(current_user))
        result = await service.user_get_address(user)
        logger.info(
            f"Address retrieved for user {user.user_id}",
            extra={"correlation_id": correlation_id},
        )
        return UserGetAddressesResponse.model_validate(result)
    except Exception as e:
        logger.error(
            f"Failed to retrieve address for user {current_user}:{e}",
            extra={"correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve address",
        )


@address_router.put(
    "/update-me",
    response_model=UserUpdateAddressesResponse,
    status_code=status.HTTP_200_OK,
)
async def user_update_address(
    data: UserUpdateAddressesRequest,
    current_user: str = CurrentUserIdDep,
    service: AddressService = AddressServiceDep,
    correlation_id: Optional[str] = None,
):
    try:
        user = CurrentUserRequest(user_id=int(current_user))
        result = await service.user_update_address(user, data)
        logger.info(
            f"Address updated for user {user.user_id}",
            extra={"correlation_id": correlation_id},
        )
        return UserUpdateAddressesResponse(
            address=AddressResponse.model_validate(result)
        )
    except Exception as e:
        logger.error(
            f"Failed to update address for user {current_user}: {e}",
            extra={"correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update address",
        )
