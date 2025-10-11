"""User API endpoints"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.app.api.dependencies import (
    CurrentUserIdDep,
    DatabaseDep,
    UserServiceDep,
)
from user_service.app.schemas.user import (
    AccountInfoResponse,
    MessageResponse,
    ReactivationRequest,
    UserLoginResponse,
    UserUpdate,
)
from user_service.app.services.user_service import UserService
from user_service.app.utils.logging import setup_user_logging

logger = setup_user_logging("users_api")
router = APIRouter()


@router.get("/me", response_model=UserLoginResponse)
async def get_current_user_info(
    user_id: str = CurrentUserIdDep,
    service: UserService = UserServiceDep,
    correlation_id: Optional[str] = None,
):
    """Get current user information"""
    try:
        user = await service.get_current_user_profile(user_id)

        logger.info(
            f"User info retrieved for user {user_id}",
            extra={"correlation_id": correlation_id},
        )
        return UserLoginResponse.model_validate(user)

    except Exception as e:
        logger.error(
            f"Failed to retrieve user info: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information",
        )


@router.get("/me/account", response_model=AccountInfoResponse)
async def get_account_information(
    user_id: str = CurrentUserIdDep,
    service: UserService = UserServiceDep,
    correlation_id: Optional[str] = None,
):
    """Get comprehensive account information for the current user"""
    try:
        account_info = await service.get_account_information(user_id)

        logger.info(
            f"Account information retrieved for user {user_id}",
            extra={"correlation_id": correlation_id},
        )
        return AccountInfoResponse(**account_info)

    except Exception as e:
        logger.error(
            f"Failed to retrieve account information: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve account information",
        )


@router.put("/me", response_model=UserLoginResponse)
async def update_current_user(
    request: Request,
    user_update: UserUpdate,
    user_id: str = CurrentUserIdDep,
    service: UserService = UserServiceDep,
    correlation_id: Optional[str] = None,
    db: AsyncSession = DatabaseDep,
):
    """Update current user information"""
    try:
        updated_user = await service.update_current_user_profile(user_id, user_update)

        logger.info(
            f"User updated: {user_id}", extra={"correlation_id": correlation_id}
        )
        return UserLoginResponse.model_validate(updated_user)

    except Exception as e:
        logger.error(
            f"Failed to update user: {str(e)}", extra={"correlation_id": correlation_id}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )


@router.post("/deactivate", response_model=MessageResponse)
async def deactivate_current_user(
    user_id: str = CurrentUserIdDep,
    service: UserService = UserServiceDep,
    correlation_id: Optional[str] = None,
):
    """Deactivate current user account"""
    try:
        await service.deactivate_account(user_id)

        logger.info(
            f"User deactivated: {user_id}",
            extra={"correlation_id": correlation_id},
        )
        return MessageResponse(message="User account deactivated successfully")

    except Exception as e:
        logger.error(
            f"Failed to deactivate user {user_id}: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate user account",
        )


@router.post("/reactivate", response_model=MessageResponse)
async def reactivate_user(
    reactivation_request: ReactivationRequest,
    service: UserService = UserServiceDep,
    correlation_id: Optional[str] = None,
):
    """Reactivate deactivated user account"""
    try:
        user = await service.reactivate_account(reactivation_request.email)

        logger.info(
            f"User reactivated: {user.id}", extra={"correlation_id": correlation_id}
        )
        return MessageResponse(message="User account reactivated successfully")

    except Exception as e:
        logger.error(
            f"Failed to reactivate user: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reactivate user account",
        )
