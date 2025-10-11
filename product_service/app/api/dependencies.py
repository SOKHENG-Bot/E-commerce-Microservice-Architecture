"""
FastAPI dependency injection for Product Service

Provides clean dependency injection for services, authentication, database sessions,
and correlation ID management. Event publishing handled by core.events module.
"""

from typing import AsyncGenerator, Optional

from app.core.database import get_db_session
from app.core.event_management import get_event_producer
from app.events.event_producers import ProductEventProducer
from app.middleware.auth.auth_middleware import (
    admin_user,
    authenticated_user,
    moderator_user,
)
from app.services.category_service import CategoryService
from app.services.inventory_service import InventoryService
from app.services.product_service import ProductService
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

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


def get_product_event_producer() -> Optional[ProductEventProducer]:
    """Provide ProductEventProducer instance"""
    return get_event_producer()


# =====================================================
# SERVICE DEPENDENCIES
# =====================================================


def get_product_service(
    session: AsyncSession = Depends(get_async_session),
    event_producer: Optional[ProductEventProducer] = Depends(
        get_product_event_producer
    ),
) -> ProductService:
    """Provide ProductService instance with database and event publishing"""
    return ProductService(session, event_producer)


def get_category_service(
    session: AsyncSession = Depends(get_async_session),
    event_producer: Optional[ProductEventProducer] = Depends(
        get_product_event_producer
    ),
) -> CategoryService:
    """Provide CategoryService instance with database and event publishing"""
    return CategoryService(session, event_producer)


def get_inventory_service(
    session: AsyncSession = Depends(get_async_session),
    event_producer: Optional[ProductEventProducer] = Depends(
        get_product_event_producer
    ),
) -> InventoryService:
    """Provide InventoryService instance with database and event publishing"""
    return InventoryService(session, event_producer)


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
        correlation_id = getattr(request.state, "request_id", None)

    return correlation_id


def get_optional_user(request: Request) -> Optional[str]:
    """Get current user if authenticated, otherwise None (for public endpoints)"""
    return getattr(request.state, "user_id", None)


# =====================================================
# COMMON DEPENDENCY ALIASES
# =====================================================
# For backward compatibility and easy use in API endpoints

CorrelationIdDep = Depends(get_correlation_id)
DatabaseDep = Depends(get_async_session)
AuthenticatedUserDep = Depends(authenticated_user)
AdminUserDep = Depends(admin_user)
ModeratorUserDep = Depends(moderator_user)
OptionalUserDep = Depends(get_optional_user)

# Service dependencies aliases
ProductServiceDep = Depends(get_product_service)
CategoryServiceDep = Depends(get_category_service)
InventoryServiceDep = Depends(get_inventory_service)
