"""
FastAPI dependency injection for User Service

Provides clean dependency injection for services, authentication, database sessions,
and correlation ID management. Event publishing handled by core.events module.
"""

from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.app.core.database import database_manager
from user_service.app.core.event_management import (
    get_event_producer as get_user_event_producer,
)
from user_service.app.events.event_producers import UserEventProducer
from user_service.app.middleware.auth.auth_middleware import (
    admin_user,
    authenticated_user,
    moderator_user,
)
from user_service.app.models.user import User
from user_service.app.services.address_service import AddressService
from user_service.app.services.auth_service import AuthService
from user_service.app.services.permission_service import PermissionService
from user_service.app.services.profile_service import ProfileService
from user_service.app.services.user_service import UserService
from user_service.app.utils.jwt_handler import JWTHandler

# =====================================================
# JWT HANDLER DEPENDENCY
# =====================================================


def get_jwt_handler() -> JWTHandler:
    """Provide JWTHandler instance"""
    from user_service.app.core.settings import get_settings

    settings = get_settings()
    return JWTHandler(secret_key=settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# Alias for backward compatibility
jwt_handler = get_jwt_handler()

# =====================================================
# DATABASE DEPENDENCIES
# =====================================================


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide async database session"""
    async with database_manager.async_session_maker() as session:  # type: ignore
        yield session


# =====================================================
# EVENT PUBLISHER DEPENDENCIES
# =====================================================


def get_event_producer() -> Optional[UserEventProducer]:
    """Provide UserEventProducer instance"""
    return get_user_event_producer()


# =====================================================
# SERVICE DEPENDENCIES
# =====================================================


def get_auth_service(
    session: AsyncSession = Depends(get_async_session),
    event_producer: Optional[UserEventProducer] = Depends(get_event_producer),
) -> AuthService:
    """Provide AuthService instance with database and event publishing"""
    return AuthService(session, event_producer)


def get_user_service(
    session: AsyncSession = Depends(get_async_session),
    event_producer: Optional[UserEventProducer] = Depends(get_event_producer),
) -> UserService:
    """Provide UserService instance with database and event publishing"""
    return UserService(session, event_producer)


def get_address_service(
    session: AsyncSession = Depends(get_async_session),
    event_producer: Optional[UserEventProducer] = Depends(get_event_producer),
) -> AddressService:
    """Provide AddressService instance with database and event publishing"""
    return AddressService(session, event_producer)


def get_profile_service(
    session: AsyncSession = Depends(get_async_session),
    event_producer: Optional[UserEventProducer] = Depends(get_event_producer),
) -> ProfileService:
    """Provide ProfileService instance with database and event publishing"""
    return ProfileService(session, event_producer)


def get_permission_service(
    session: AsyncSession = Depends(get_async_session),
) -> PermissionService:
    """Provide PermissionService instance with database session"""
    return PermissionService(session)


# =====================================================
# AUTHENTICATION & REQUEST CONTEXT DEPENDENCIES
# =====================================================


def get_correlation_id(request: Request) -> Optional[str]:
    """Extract correlation ID from request headers or state"""
    # Check headers first (from API Gateway)
    correlation_id = (
        request.headers.get("X-Correlation-ID")
        or request.headers.get("correlation-id")
        or request.headers.get("x-request-id")
    )

    # Fallback to request state (from middleware)
    if not correlation_id:
        correlation_id = getattr(request.state, "correlation_id", None)

    return correlation_id


def get_current_user_id(request: Request) -> str:
    """Get current authenticated user ID from middleware state"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return str(user_id)


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Get current authenticated user object from database"""
    # Get user ID from middleware state
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Fetch user from database
    query = select(User).where(User.id == int(user_id))
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


# =====================================================
# COMMON DEPENDENCY ALIASES
# =====================================================
# For backward compatibility and easy use in API endpoints

CorrelationIdDep = Depends(get_correlation_id)
DatabaseDep = Depends(get_async_session)
AuthenticatedUserDep = Depends(authenticated_user)
AdminUserDep = Depends(admin_user)
ModeratorUserDep = Depends(moderator_user)
CurrentUserIdDep = Depends(get_current_user_id)

# Service dependencies aliases
AuthServiceDep = Depends(get_auth_service)
UserServiceDep = Depends(get_user_service)
AddressServiceDep = Depends(get_address_service)
ProfileServiceDep = Depends(get_profile_service)
PermissionServiceDep = Depends(get_permission_service)
