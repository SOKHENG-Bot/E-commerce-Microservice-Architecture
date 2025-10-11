"""
FastAPI dependency injection for Order Service

Provides clean dependency injection for services, authentication, database sessions,
and correlation ID management. Event publishing handled by core.events module.
"""

from typing import AsyncGenerator, Optional

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db_session
from ..core.events import get_event_producer
from ..events.producers import OrderEventProducer
from ..middleware.auth import admin_user, authenticated_user
from ..services.order_service import OrderService

# =====================================================
# DATABASE DEPENDENCIES
# =====================================================


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide async database session"""
    async for session in get_db_session():
        yield session


# =====================================================
# EVENT PUBLISHER DEPENDENCIES
# =====================================================


def get_order_event_producer() -> Optional[OrderEventProducer]:
    """Provide OrderEventProducer instance"""
    return get_event_producer()


# =====================================================
# SERVICE DEPENDENCIES
# =====================================================


def get_order_service(
    session: AsyncSession = Depends(get_async_session),
    event_producer: Optional[OrderEventProducer] = Depends(get_order_event_producer),
) -> OrderService:
    """Provide OrderService instance with database and event publishing"""
    return OrderService(session, event_producer)


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
    from fastapi import HTTPException

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return str(user_id)


def get_current_user_role(request: Request) -> Optional[str]:
    """Get current authenticated user role from middleware state"""
    return getattr(request.state, "user_role", None)


# =====================================================
# COMMON DEPENDENCY ALIASES
# =====================================================
# For backward compatibility and easy use in API endpoints

# Core dependencies
CorrelationIdDep = Depends(get_correlation_id)
DatabaseDep = Depends(get_async_session)

# Authentication dependencies (handled by auth middleware)
CurrentUserDep = Depends(authenticated_user)
AdminUserDep = Depends(admin_user)
CurrentUserIdDep = Depends(get_current_user_id)
CurrentUserRoleDep = Depends(get_current_user_role)

# Service dependencies aliases
OrderServiceDep = Depends(get_order_service)
OrderEventProducerDep = Depends(get_order_event_producer)
