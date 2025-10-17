"""
Auth Service - Core Functions Only
Business logic for essential user authentication operations
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from fastapi.requests import Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from user_service.app.models.address import Address
from user_service.app.models.profile import Profile
from user_service.app.models.user import Permission, Role, User
from user_service.app.repository.address_repository import AddressRepository
from user_service.app.repository.profile_repository import ProfileRepository
from user_service.app.repository.user_repository import UserRepository
from user_service.app.schemas.user import (
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    UserCreate,
)
from user_service.app.utils.jwt_handler import JWTHandler

from ..core.access_permissions import PermissionEnum
from ..core.password_security import SecurityUtils
from ..core.settings import get_settings
from ..events.event_producers import UserEventProducer
from ..utils.logging import setup_user_logging as setup_logging

settings = get_settings()
logger = setup_logging("user_service.auth", log_level=settings.LOG_LEVEL)

jwt_handler = JWTHandler(secret_key=settings.SECRET_KEY, algorithm=settings.ALGORITHM)


class AuthService:
    def __init__(
        self, session: AsyncSession, event_publisher: Optional[UserEventProducer] = None
    ):
        self.session = session
        self.event_publisher = event_publisher
        self.user_repository = UserRepository(session)
        self.address_repository = AddressRepository(session)
        self.profile_repository = ProfileRepository(session)

    async def register_user(self, data: UserCreate) -> dict[str, str]:
        """Register a new user"""
        import time

        logger.info(
            "User registration started",
            extra={
                "email": data.email,
                "username": getattr(data, "username", None),
                "phone_number": getattr(data, "phone_number", None),
            },
        )

        try:
            # Check for existing user
            existing_check_start = time.time()
            existing_user = await self.user_repository.query_email(data.email)
            existing_check_duration = int((time.time() - existing_check_start) * 1000)

            logger.debug(
                "Existing user check completed",
                extra={
                    "email": data.email,
                    "duration_ms": existing_check_duration,
                    "user_exists": existing_user is not None,
                },
            )

            if existing_user:
                logger.warning(
                    "Registration failed - email already exists",
                    extra={
                        "email": data.email,
                        "existing_user_id": str(existing_user.id),
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered.",
                )

            # Fetch default role or create default role
            role_stmt = await self.session.execute(
                select(Role).where(Role.name == "customer")
            )
            role = role_stmt.scalars().first()
            if not role:
                role = Role(
                    name="customer",
                    description="Regular customer with basic access",
                )
                self.session.add(role)
                await self.session.flush()

            # Fetch default permission or create default permission
            permission_stmt = await self.session.execute(
                select(Permission).where(Permission.name == PermissionEnum.READ_USER)
            )
            permission = permission_stmt.scalars().first()
            if not permission:
                permission = Permission(name=PermissionEnum.READ_USER)
                self.session.add(permission)
                await self.session.flush()

            user = User(
                email=data.email,
                password_hash=SecurityUtils.hash_password(data.password),
                roles=[role],
            )

            # Add user to session but don't commit yet
            self.session.add(user)
            await self.session.flush()  # Get the user.id without committing

            # Create related records
            profile = Profile(user_id=user.id, gender=None)

            # Create default billing address
            address = Address(
                user_id=user.id,
                type="billing",
                is_default=True,
            )

            # Add all to session
            self.session.add(profile)
            self.session.add(address)

            # Commit everything in one transaction
            await self.session.commit()
            await self.session.refresh(user)
            new_user = user

            token_data: dict[str, Any] = {
                "user_id": str(new_user.id),
                "email": new_user.email,
                "jti": str(uuid.uuid4()),
            }
            verify_token = jwt_handler.encode_token(
                token_data, expires_delta=timedelta(minutes=5)
            )  # 5 minutes for email verification

            # Publish user created event
            if self.event_publisher:
                try:
                    await self.event_publisher.publish_user_created(new_user)
                    logger.info(
                        "User created event published successfully",
                        extra={
                            "user_id": str(new_user.id),
                            "email": new_user.email,
                        },
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to publish user created event: {e}",
                        extra={
                            "user_id": str(new_user.id),
                            "email": new_user.email,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )
            logger.info(
                "User created event published, now checking email verification",
                extra={
                    "user_id": str(new_user.id),
                    "email": new_user.email,
                },
            )

            # Publish email verification request event
            logger.info(
                "Checking event publisher availability",
                extra={
                    "user_id": str(new_user.id),
                    "email": new_user.email,
                    "event_publisher_exists": self.event_publisher is not None,
                },
            )

            # Publish email verification request event
            if self.event_publisher:
                try:
                    await self.event_publisher.publish_email_verification_request(
                        user=new_user,
                        verification_token=verify_token,
                        expires_in_minutes=5,
                    )
                    logger.info(
                        "Successfully published email verification request event",
                        extra={
                            "user_id": str(new_user.id),
                            "email": new_user.email,
                        },
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to publish email verification request event: {e}",
                        extra={
                            "user_id": str(new_user.id),
                            "email": new_user.email,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )
            else:
                logger.warning(
                    "Event publisher is None - email verification event not published",
                    extra={
                        "user_id": str(new_user.id),
                        "email": new_user.email,
                    },
                )

            logger.info(
                "About to return from register_user function",
                extra={
                    "user_id": str(new_user.id),
                    "email": new_user.email,
                },
            )
            return {
                "verify_token": verify_token,
                "expires_in_minutes": str(5),  # 5 minutes
            }

        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error during user registration: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed.",
            )

    async def verify_email_token(self, token: str) -> bool:
        """Verify user email with token"""
        try:
            logger.info(f"Starting email verification for token: {token[:20]}...")
            # Decode and validate the token
            payload = jwt_handler.decode_token(token)
            logger.info(
                f"Token decoded successfully: user_id={payload.user_id}, email={payload.email}"
            )
            email = payload.email
            if not email:
                logger.error("Token missing email field")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token.",
                )
            # Query user by email, mark as verified, and update record to database
            user = await self.user_repository.query_email(email)
            logger.info(
                f"Found user: {user.id if user else None}, email matches: {user.email == email if user else False}"
            )
            if not user or user.email != email:
                logger.error(
                    f"User not found or email mismatch: requested={email}, found={user.email if user else None}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found.",
                )
            if user.is_verified:
                logger.info("User already verified")
                return True
            user.is_verified = True
            await self.user_repository.update(user)

            # Publish email verification confirmation event
            if self.event_publisher:
                try:
                    await self.event_publisher.publish_confirm_email_verification(user)
                    logger.info(
                        "Email verification confirmation event published successfully",
                        extra={
                            "user_id": str(user.id),
                            "email": user.email,
                        },
                    )
                    logger.info(
                        "User email verified successfully.",
                        extra={
                            "user_id": str(user.id),
                            "email": user.email,
                        },
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to publish email verification confirmation event: {e}",
                        extra={
                            "user_id": str(user.id),
                            "email": user.email,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )
            else:
                logger.warning(
                    "Event publisher is None - email verification confirmation event not published",
                    extra={
                        "user_id": str(user.id),
                        "email": user.email,
                    },
                )
            logger.info(
                "User email verified successfully.",
                extra={
                    "user_id": str(user.id),
                    "email": user.email,
                },
            )

            return True
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during email verification: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Email verification failed.",
            )

    async def authenticate_user(
        self,
        data: LoginRequest,
        request: Request,
        response: Response,
    ) -> User:
        """Authenticate user login"""
        try:
            user = await self.user_repository.query_email(data.email)
            if not user or not SecurityUtils.verify_password(
                data.password, user.password_hash
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password.",
                )
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive.",
                )
            # Update last login timestamp
            user.last_login = datetime.now(timezone.utc)
            await self.user_repository.update(user)

            token_data: dict[str, Any] = {
                "user_id": str(user.id),
                "email": user.email,
                "username": user.username,
                "jti": str(uuid.uuid4()),
            }

            access_token = jwt_handler.encode_token(
                token_data,
                expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            )

            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                path="/",
                # secure=False,
                samesite="lax",
            )

            login_details: dict[str, Optional[str]] = {
                "login_timestamp": datetime.now(timezone.utc).isoformat(),
                "device_type": request.headers.get("User-Agent"),
                "ip_address": request.client.host if request.client else None,
            }

            if self.event_publisher:
                await self.event_publisher.publish_user_login(
                    user=user,
                    login_ip=login_details.get("ip_address") or "unknown",
                )
            logger.info(
                "User authenticated successfully.",
                extra={
                    "user_id": str(user.id),
                    "email": user.email,
                },
            )
            return user
        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error during user authentication: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication failed.",
            )

    async def forgot_password(self, data: PasswordResetRequest) -> dict[str, str]:
        """Request password reset"""
        try:
            user = await self.user_repository.query_email(data.email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User with this email does not exist.",
                )
            token_data: dict[str, Any] = {
                "user_id": str(user.id),
                "email": user.email,
                "username": user.username,
                "jti": str(uuid.uuid4()),
            }
            reset_token = jwt_handler.encode_token(
                token_data, expires_delta=timedelta(minutes=15)
            )  # 15 minutes

            # Publish password reset request event
            if self.event_publisher:
                await self.event_publisher.publish_password_reset_request(
                    user, reset_token
                )

            logger.info(
                "Password reset requested.",
                extra={
                    "user_id": str(user.id),
                    "email": user.email,
                },
            )
            return {
                "reset_token": reset_token,
                "expires_in_minutes": str(15),
            }  # 15 minutes in seconds
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during password reset request: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password reset request failed.",
            )

    async def reset_password(self, data: PasswordResetConfirm) -> User:
        """Reset password with token"""
        try:
            user = await self.user_repository.query_email(data.email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User with this email does not exist.",
                )
            user.password_hash = SecurityUtils.hash_password(data.new_password)
            updated_user = await self.user_repository.update(user)

            # Publish password reset confirm event
            if self.event_publisher:
                await self.event_publisher.publish_password_reset_confirm(updated_user)

            logger.info(
                "Password reset successfully.",
                extra={
                    "user_id": str(user.id),
                    "email": user.email,
                },
            )
            return updated_user
        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error during password reset: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password reset failed.",
            )

    async def change_password(
        self, data: PasswordChangeRequest, current_user: User
    ) -> User:
        """Change password when logged in"""
        try:
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User is not authenticated.",
                )
            user = await self.user_repository.query_email(current_user.email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User with this email does not exist.",
                )
            if not SecurityUtils.verify_password(
                data.current_password, user.password_hash
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Current password is incorrect.",
                )
            user.password_hash = SecurityUtils.hash_password(data.new_password)
            updated_user = await self.user_repository.update(user)
            logger.info(
                "Password changed successfully.",
                extra={
                    "user_id": str(user.id),
                    "email": user.email,
                },
            )
            return updated_user
        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error during password change: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password change failed.",
            )

    async def logout_user(
        self, current_user: User, response: Response
    ) -> dict[str, str]:
        """Logout user"""
        try:
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User is not authenticated.",
                )
            response.delete_cookie(key="access_token")

            # Publish logout event
            if self.event_publisher:
                await self.event_publisher.publish_logout(current_user)

            logger.info(
                "User logged out successfully.",
                extra={
                    "user_id": str(current_user.id),
                    "email": current_user.email,
                },
            )
            return {"Message": "Logged out successfully."}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during user logout: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout failed.",
            )

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh access token using refresh token"""
        try:
            # Decode refresh token
            payload = jwt_handler.decode_token(refresh_token)
            user_id = payload.user_id
            email = payload.email

            if not user_id or not email:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token.",
                )

            # Verify user still exists and is active
            user = await self.user_repository.query_email(email)
            if not user or not user.is_active or str(user.id) != user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid user or user inactive.",
                )

            # Generate new access token
            token_data: dict[str, Any] = {
                "user_id": str(user.id),
                "email": user.email,
                "username": user.username,
                "jti": str(uuid.uuid4()),
            }

            new_access_token = jwt_handler.encode_token(
                token_data,
                expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            )

            logger.info(
                "Access token refreshed successfully.",
                extra={
                    "user_id": str(user.id),
                    "email": user.email,
                },
            )

            return {
                "access_token": new_access_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during token refresh: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token refresh failed.",
            )
