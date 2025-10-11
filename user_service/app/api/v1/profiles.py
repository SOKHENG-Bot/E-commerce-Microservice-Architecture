"""Profile API endpoints"""

from typing import Optional

from fastapi import APIRouter, HTTPException, status

from user_service.app.api.dependencies import CurrentUserIdDep, ProfileServiceDep
from user_service.app.schemas.profile import (
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
)
from user_service.app.services.profile_service import ProfileService
from user_service.app.utils.logging import setup_user_logging

logger = setup_user_logging("profiles_api")
router = APIRouter(prefix="/profiles")


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    user_id: str = CurrentUserIdDep,
    service: ProfileService = ProfileServiceDep,
    correlation_id: Optional[str] = None,
):
    """Get the current user's profile information"""
    try:
        profile = await service.get_profile(user_id)
        if not profile:
            logger.warning(
                f"Profile not found for user {user_id}",
                extra={"correlation_id": correlation_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )

        logger.info(
            f"Profile retrieved for user {user_id}",
            extra={"correlation_id": correlation_id},
        )
        return profile

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to retrieve profile: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile",
        )


@router.post("/", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: ProfileCreate,
    user_id: str = CurrentUserIdDep,
    service: ProfileService = ProfileServiceDep,
    correlation_id: Optional[str] = None,
):
    """Create a new profile for the current user"""
    try:
        # Check if profile already exists
        existing_profile = await service.get_profile(user_id)
        if existing_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Profile already exists"
            )

        profile = await service.create_profile(user_id, profile_data)

        logger.info(
            f"Profile created for user {user_id}",
            extra={"correlation_id": correlation_id},
        )
        return profile

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to create profile: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create profile",
        )


@router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    profile_update: ProfileUpdate,
    user_id: str = CurrentUserIdDep,
    service: ProfileService = ProfileServiceDep,
    correlation_id: Optional[str] = None,
):
    """Update the current user's profile"""
    try:
        # Get current profile for comparison
        current_profile = await service.get_profile(user_id)
        if not current_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )

        # Update profile
        updated_profile = await service.update_profile(user_id, profile_update)

        logger.info(
            f"Profile updated for user {user_id}",
            extra={"correlation_id": correlation_id},
        )
        return updated_profile

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to update profile: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )
