"""
FastAPI dependency injection for Notification Service

Provides clean dependency injection for services, authentication, and database sessions.
Event publishing and API logging have been moved to dedicated modules.
"""

from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import database_manager
from ..core.events import get_event_producer
from ..events.producers import NotificationEventProducer
from ..services.notification_service import NotificationService

# =====================================================
# DATABASE DEPENDENCIES
# =====================================================


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide async database session with commit on success"""
    async with database_manager.async_session_maker() as session:
        try:
            yield session
            # Commit on successful completion
            await session.commit()
        except Exception:
            # Rollback on error
            await session.rollback()
            raise


# =====================================================
# EVENT PUBLISHER DEPENDENCIES
# =====================================================


def get_notification_event_producer() -> NotificationEventProducer:
    """Provide NotificationEventProducer instance"""
    producer = get_event_producer()
    if producer is None:
        raise HTTPException(status_code=500, detail="Event producer not available")
    return producer


# =====================================================
# SERVICE DEPENDENCIES
# =====================================================


def get_notification_service(
    session: AsyncSession = Depends(get_async_session),
    event_producer: NotificationEventProducer = Depends(
        get_notification_event_producer
    ),
) -> NotificationService:
    """Provide NotificationService instance with database and event publishing"""
    return NotificationService(session, event_producer)


# =====================================================
# AUTHENTICATION DEPENDENCIES
# =====================================================


def get_current_user(request: Request) -> str:
    """Get current authenticated user from request state"""
    if not hasattr(request.state, "user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return request.state.user_id


def get_current_admin_user(request: Request) -> str:
    """Get current authenticated admin user from request state"""
    if not hasattr(request.state, "user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    if not getattr(request.state, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    return request.state.user_id


def get_optional_user(request: Request) -> Optional[str]:
    """Get current user if authenticated, otherwise None (for public endpoints)"""
    return getattr(request.state, "user_id", None)


# =====================================================
# COMMON DEPENDENCY ALIASES
# =====================================================
# For backward compatibility and easy use in API endpoints

# Database and session dependencies
DatabaseDep = Depends(get_async_session)

# Event publisher dependencies
EventProducerDep = Depends(get_notification_event_producer)

# Authentication dependencies
CurrentUserDep = Depends(get_current_user)
AdminUserDep = Depends(get_current_admin_user)
OptionalUserDep = Depends(get_optional_user)

# Service dependencies aliases
NotificationServiceDep = Depends(get_notification_service)
