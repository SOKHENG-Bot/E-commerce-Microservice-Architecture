from typing import Optional

from fastapi import APIRouter, status
from fastapi.requests import Request
from fastapi.responses import Response

from user_service.app.api.dependencies import (
    AuthenticatedUserDep,
    AuthServiceDep,
    CorrelationIdDep,
    CurrentUserIdDep,
)
from user_service.app.models.user import User
from user_service.app.schemas.user import (
    CurrentUserRequest,
    UserChangePasswordRequest,
    UserChangePasswordResponse,
    UserForgotPasswordRequest,
    UserForgotPasswordResponse,
    UserLoginRequest,
    UserLoginResponse,
    UserLogoutResponse,
    UserRefreshTokenRequest,
    UserRefreshTokenResponse,
    UserRegistrationRequest,
    UserRegistrationResponse,
    UserResetPasswordRequest,
    UserResetPasswordResponse,
    UserVerificationRequest,
    UserVerificationResponse,
)
from user_service.app.services.auth_service import AuthService
from user_service.app.utils.logging import setup_user_logging

logger = setup_user_logging("auth_api")
router = APIRouter(prefix="/auth")


@router.post(
    "/register",
    response_model=UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: UserRegistrationRequest,
    service: AuthService = AuthServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
) -> UserRegistrationResponse:
    try:
        await service.register_user(data)
        logger.info(
            f"User registered successfully: {data.email}",
            extra={"correlation_id": correlation_id},
        )
        return UserRegistrationResponse(
            message="User registered successfully. Please check your email for verification."
        )
    except Exception as e:
        logger.error(
            f"Registration failed for {data.email}: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise


@router.get(
    "/verify-email-token/{token}",
    response_model=UserVerificationResponse,
    status_code=status.HTTP_200_OK,
)
async def verify_email_token(
    data: UserVerificationRequest,
    service: AuthService = AuthServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
) -> UserVerificationResponse:
    try:
        result = await service.verify_email_token(data)
        logger.info(
            f"Email verification result: {result}",
            extra={"correlation_id": correlation_id},
        )
        return UserVerificationResponse(
            verified=result,
            message="Email verified successfully"
            if result
            else "Email verification failed",
        )
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
    data: UserLoginRequest,
    service: AuthService = AuthServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
) -> UserLoginResponse:
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


@router.post(
    "/forgot-password",
    response_model=UserForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
)
async def forgot_password(
    data: UserForgotPasswordRequest,
    service: AuthService = AuthServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
) -> UserForgotPasswordResponse:
    try:
        result = await service.forgot_password(data)
        logger.info(
            f"Password reset requested for: {data.email}",
            extra={"correlation_id": correlation_id},
        )
        return UserForgotPasswordResponse(
            message=result.get(
                "message", "Please check your email for password reset instructions."
            )
        )
    except Exception as e:
        logger.error(
            f"Password reset request failed for {data.email}: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise


@router.post(
    "/reset-password",
    response_model=UserResetPasswordResponse,
    status_code=status.HTTP_200_OK,
)
async def reset_password(
    data: UserResetPasswordRequest,
    service: AuthService = AuthServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
) -> UserResetPasswordResponse:
    try:
        result = await service.reset_password(data)
        logger.info(
            f"Password reset completed for user: {result.id}",
            extra={"correlation_id": correlation_id},
        )
        return UserResetPasswordResponse.model_validate(result)
    except Exception as e:
        logger.error(
            f"Password reset failed: {str(e)}", extra={"correlation_id": correlation_id}
        )
        raise


@router.post(
    "/change-password",
    response_model=UserChangePasswordResponse,
    status_code=status.HTTP_200_OK,
)
async def change_password(
    data: UserChangePasswordRequest,
    current_user: str = CurrentUserIdDep,
    service: AuthService = AuthServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
) -> UserChangePasswordResponse:
    try:
        user = CurrentUserRequest(user_id=int(current_user))
        result = await service.change_password(user, data)
        logger.info(
            f"Password changed for user: {result.id}",
            extra={"correlation_id": correlation_id},
        )
        return UserChangePasswordResponse(message="Password changed successfully")
    except Exception as e:
        logger.error(
            f"Password change failed for user {current_user}: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise


@router.post(
    "/refresh-token",
    response_model=UserRefreshTokenResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh_token(
    data: UserRefreshTokenRequest,
    service: AuthService = AuthServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
) -> UserRefreshTokenResponse:
    try:
        result = await service.refresh_access_token(data)
        logger.info(
            "Access token refreshed successfully",
            extra={"correlation_id": correlation_id},
        )
        return UserRefreshTokenResponse.model_validate(result)
    except Exception as e:
        logger.error(
            f"Token refresh failed: {str(e)}", extra={"correlation_id": correlation_id}
        )
        raise


@router.post(
    "/logout", response_model=UserLogoutResponse, status_code=status.HTTP_200_OK
)
async def logout(
    response: Response,
    current_user: User = AuthenticatedUserDep,
    service: AuthService = AuthServiceDep,
    correlation_id: Optional[str] = CorrelationIdDep,
) -> UserLogoutResponse:
    try:
        result = await service.logout_user(current_user, response)
        logger.info(
            f"User logout successful: {current_user.id}",
            extra={"correlation_id": correlation_id},
        )
        return UserLogoutResponse(
            message=result.get("message", "Logged out successfully")
        )
    except Exception as e:
        logger.error(
            f"Logout failed for user {current_user.id}: {str(e)}",
            extra={"correlation_id": correlation_id},
        )
        raise
