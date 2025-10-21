from typing import Optional

from fastapi import APIRouter, HTTPException, status

from user_service.app.api.dependencies import (
    CorrelationIdDep,
    CurrentUserIdDep,
    ProfileServiceDep,
)
from user_service.app.schemas.user import (
    CurrentUserRequest,
    ProfileResponse,
    UserGetProfileResponse,
    UserUpdateProfileRequest,
    UserUpdateProfileResponse,
)
from user_service.app.services.profile_service import ProfileService
from user_service.app.utils.logging import setup_user_logging

logger = setup_user_logging("profiles_api")
router = APIRouter(prefix="/profiles")


@router.get(
    "/",
    response_model=UserGetProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def user_get_profile(
    current_user: str = CurrentUserIdDep,
    service: ProfileService = ProfileServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
) -> UserGetProfileResponse:
    try:
        user = CurrentUserRequest(user_id=int(current_user))
        result = await service.user_get_profile(user)
        logger.info(
            f"Profile retrieved for user {user.user_id}",
            extra={"correlation_id": correlation_id},
        )
        return UserGetProfileResponse(profile=ProfileResponse.model_validate(result))
    except Exception as e:
        logger.error(
            f"Failed to retrieve profile: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile",
        )


@router.put("/update-me", response_model=UserUpdateProfileResponse)
async def user_update_profile(
    data: UserUpdateProfileRequest,
    current_user: str = CurrentUserIdDep,
    service: ProfileService = ProfileServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
):
    try:
        user = CurrentUserRequest(user_id=int(current_user))
        result = await service.user_update_profile(user, data)
        logger.info(
            f"Profile updated for user {result.id}",
            extra={"correlation_id": correlation_id},
        )
        return UserUpdateProfileResponse(profile=ProfileResponse.model_validate(result))
    except Exception as e:
        logger.error(
            f"Failed to update profile: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )
