from typing import Optional

from fastapi import APIRouter, HTTPException, status

from user_service.app.api.dependencies import (
    CorrelationIdDep,
    CurrentUserIdDep,
    UserServiceDep,
)
from user_service.app.schemas.user import (
    CurrentUserRequest,
    UserGetAccountInfoResponse,
    UserUpdateAccountInfoRequest,
    UserUpdateAccountInfoResponse,
)
from user_service.app.services.user_service import UserService
from user_service.app.utils.logging import setup_user_logging

logger = setup_user_logging("users_api")
router = APIRouter()


@router.get(
    "/",
    response_model=UserGetAccountInfoResponse,
    status_code=status.HTTP_200_OK,
)
async def get_account_information(
    current_user: str = CurrentUserIdDep,
    service: UserService = UserServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
) -> UserGetAccountInfoResponse:
    try:
        user = CurrentUserRequest(user_id=int(current_user))
        result = await service.user_get_account_info(user)
        logger.info(
            f"Account information retrieved for user {user.user_id}",
            extra={"correlation_id": correlation_id},
        )
        return UserGetAccountInfoResponse(**result)
    except Exception as e:
        logger.error(
            f"Failed to retrieve account information: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve account information",
        )


@router.put("/update-me", response_model=UserUpdateAccountInfoResponse)
async def update_current_user(
    data: UserUpdateAccountInfoRequest,
    current_user: str = CurrentUserIdDep,
    service: UserService = UserServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
) -> UserUpdateAccountInfoResponse:
    try:
        user = CurrentUserRequest(user_id=int(current_user))
        result = await service.user_update_account_info(user, data)
        logger.info(
            f"User updated: {user.user_id}",
            extra={"correlation_id": correlation_id},
        )
        return UserUpdateAccountInfoResponse.model_validate(result)
    except Exception as e:
        logger.error(
            f"Failed to update user: {str(e)}", extra={"correlation_id": correlation_id}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )
