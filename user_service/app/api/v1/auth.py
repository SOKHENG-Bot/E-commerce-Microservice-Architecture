"""Authentication API endpoints"""

from typing import Dict, Optional

from fastapi import APIRouter, status
from fastapi.requests import Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.app.api.dependencies import (
    AuthenticatedUserDep,
    AuthServiceDep,
    CorrelationIdDep,
    DatabaseDep,
)
from user_service.app.models.user import User
from user_service.app.schemas.user import (
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLoginResponse,
)
from user_service.app.services.auth_service import AuthService
from user_service.app.utils.logging import setup_user_logging

logger = setup_user_logging("auth_api")
router = APIRouter(prefix="/auth")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    data: UserCreate,
    service: AuthService = AuthServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
) -> Dict[str, str]:
    """Register a new user account"""
    try:
        result = await service.register_user(data)

        logger.info(
            f"User registered successfully: {data.email}",
            extra={"correlation_id": correlation_id},
        )
        return result

    except Exception as e:
        logger.error(
            f"Registration failed for {data.email}: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise


@router.get("/verify-email-token/{token}", status_code=status.HTTP_200_OK)
async def verify_email_token(
    token: str,
    service: AuthService = AuthServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
) -> Dict[str, bool]:
    """Verify user's email address using verification token"""
    try:
        result = await service.verify_email_token(token)

        logger.info(
            f"Email verification result: {result}",
            extra={"correlation_id": correlation_id},
        )
        return {"verified": result}

    except Exception as e:
        logger.error(
            f"Email verification failed: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise


@router.post("/login", response_model=UserLoginResponse, status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
    service: AuthService = AuthServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
) -> UserLoginResponse:
    """Authenticate user and return user data with cookies"""
    try:
        result = await service.authenticate_user(data, request, response)

        logger.info(
            f"User login successful: {data.email}",
            extra={"correlation_id": correlation_id},
        )
        return UserLoginResponse.model_validate(result)

    except Exception as e:
        logger.error(
            f"Login failed for {data.email}: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    current_user: User = AuthenticatedUserDep,
    service: AuthService = AuthServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
) -> Dict[str, str]:
    """Logout user and clear authentication cookies"""
    try:
        result = await service.logout_user(current_user, response)

        logger.info(
            f"User logout successful: {current_user.id}",
            extra={"correlation_id": correlation_id},
        )
        return result

    except Exception as e:
        logger.error(
            f"Logout failed for user {current_user.id}: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    data: PasswordResetRequest,
    service: AuthService = AuthServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
) -> Dict[str, str]:
    """Request password reset token"""
    try:
        result = await service.forgot_password(data)

        logger.info(
            f"Password reset requested for: {data.email}",
            extra={"correlation_id": correlation_id},
        )
        return result

    except Exception as e:
        logger.error(
            f"Password reset request failed for {data.email}: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    data: PasswordResetConfirm,
    service: AuthService = AuthServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
) -> UserLoginResponse:
    """Reset user password using reset token"""
    try:
        result = await service.reset_password(data)

        logger.info(
            f"Password reset completed for user: {result.id}",
            extra={"correlation_id": correlation_id},
        )
        return UserLoginResponse.model_validate(result)

    except Exception as e:
        logger.error(
            f"Password reset failed: {str(e)}", extra={"correlation_id": correlation_id}
        )
        raise


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    request: Request,
    data: PasswordChangeRequest,
    current_user: User = AuthenticatedUserDep,
    service: AuthService = AuthServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
    db: AsyncSession = DatabaseDep,
) -> Dict[str, str]:
    """Change user password (authenticated)"""
    try:
        await service.change_password(data, current_user)

        logger.info(
            f"Password changed for user: {current_user.id}",
            extra={"correlation_id": correlation_id},
        )
        return {"message": "Password changed successfully"}

    except Exception as e:
        logger.error(
            f"Password change failed for user {current_user.id}: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise


@router.post(
    "/refresh-token", response_model=TokenResponse, status_code=status.HTTP_200_OK
)
async def refresh_token(
    data: RefreshTokenRequest,
    service: AuthService = AuthServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
) -> TokenResponse:
    """Refresh access token using refresh token"""
    try:
        result = await service.refresh_access_token(data.refresh_token)

        logger.info(
            "Access token refreshed successfully",
            extra={"correlation_id": correlation_id},
        )
        return TokenResponse(**result)

    except Exception as e:
        logger.error(
            f"Token refresh failed: {str(e)}", extra={"correlation_id": correlation_id}
        )
        raise
