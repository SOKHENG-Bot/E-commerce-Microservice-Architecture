"""
User Service FastAPI Application
==============================

Main application entry point for the User Service microservice.
Handles user management, authentication, profiles, addresses, and permissions.
Provides REST API endpoints with comprehensive middleware stack for security,
monitoring, and performance optimization.
"""

import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# API routers
from user_service.app.api.v1.addresses import address_router
from user_service.app.api.v1.auth import router as auth_router
from user_service.app.api.v1.health import router as health_router
from user_service.app.api.v1.permissions import router as permissions_router
from user_service.app.api.v1.profiles import router as profile_router
from user_service.app.api.v1.users import router as user_router

# Core imports
from user_service.app.core.database import database_manager
from user_service.app.core.event_management import close_events, init_events
from user_service.app.core.settings import get_settings

# Add project root to path for shared modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
settings = get_settings()
environment = os.getenv("ENVIRONMENT", "development").lower()
enable_file_logging = environment in ["production", "staging"]


def _setup_application_logging():
    """Setup application logging with fallback support."""
    try:
        from app.utils.logging import setup_user_logging as setup_logging
    except ImportError:
        # Fallback logging setup
        import logging

        def setup_logging(
            service_name: str,
            log_level: str = "INFO",
            enable_file_logging: bool = False,
            log_dir: Optional[str] = None,
            max_file_size: int = 100 * 1024 * 1024,
            backup_count: int = 5,
            exclude_fields: Optional[List[str]] = None,
            enable_performance_logging: bool = True,
        ) -> logging.Logger:
            return logging.getLogger(service_name)

    return setup_logging(
        "user_service",
        log_level=settings.LOG_LEVEL,
        enable_file_logging=enable_file_logging,
        enable_performance_logging=True,
    )


logger = _setup_application_logging()


# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown."""
    startup_start = time.time()

    try:
        await _initialize_services(app, startup_start)
    except Exception as e:
        await _handle_startup_error(startup_start, e)
        raise

    yield

    await _shutdown_services()


async def _initialize_services(app: FastAPI, startup_start: float) -> None:
    """Initialize all application services during startup."""
    logger.info(
        "Starting user service initialization",
        extra={
            "environment": environment,
            "debug_mode": settings.DEBUG,
            "file_logging_enabled": enable_file_logging,
            "service_version": settings.APP_VERSION,
        },
    )

    # Initialize event publisher (independent of database)
    event_duration = await _init_event_publisher()

    # Initialize database (required)
    db_duration = await _init_database()

    # Initialize event consumer (depends on database)
    consumer_duration = await _init_event_consumer(app)

    # Log successful startup
    total_startup = int((time.time() - startup_start) * 1000)
    logger.info(
        "User service started successfully",
        extra={
            "total_startup_duration_ms": total_startup,
            "database_init_ms": db_duration,
            "event_publisher_init_ms": event_duration,
            "event_consumer_init_ms": consumer_duration,
        },
    )


async def _init_event_publisher() -> int:
    """Initialize event publisher and return duration in ms."""
    start_time = time.time()
    await init_events()
    duration = int((time.time() - start_time) * 1000)
    logger.info("Event publisher started", extra={"duration_ms": duration})
    return duration


async def _init_database() -> int:
    """Initialize database and return duration in ms."""
    start_time = time.time()
    await database_manager.create_tables()
    duration = int((time.time() - start_time) * 1000)
    logger.info("Database initialization completed", extra={"duration_ms": duration})
    return duration


async def _init_event_consumer(app: FastAPI) -> int:
    """Initialize event consumer and return duration in ms."""
    start_time = time.time()

    from user_service.app.events.event_consumers import UserEventConsumer

    async with database_manager.async_session_maker() as consumer_session:
        consumer = UserEventConsumer(consumer_session)
        app.state.event_consumer = consumer
        await consumer.start()

    duration = int((time.time() - start_time) * 1000)
    logger.info("Event consumer started", extra={"duration_ms": duration})
    return duration


async def _handle_startup_error(startup_start: float, error: Exception) -> None:
    """Handle startup errors with proper logging."""
    logger.error(
        "Failed to start user service",
        exc_info=True,
        extra={
            "startup_duration_ms": int((time.time() - startup_start) * 1000),
            "error_type": type(error).__name__,
        },
    )


async def _shutdown_services() -> None:
    """Shutdown all application services gracefully."""
    shutdown_start = time.time()

    try:
        logger.info("Starting user service shutdown")

        # Stop event consumer
        if hasattr(app.state, "event_consumer"):
            await app.state.event_consumer.stop()

        await close_events()

        shutdown_duration = int((time.time() - shutdown_start) * 1000)
        logger.info(
            "User service shutdown completed",
            extra={"shutdown_duration_ms": shutdown_duration},
        )

    except Exception as e:
        logger.error(
            "Error during user service shutdown",
            exc_info=True,
            extra={
                "shutdown_duration_ms": int((time.time() - shutdown_start) * 1000),
                "error_type": type(e).__name__,
            },
        )
        raise


# Application factory
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # Setup application components
    _setup_middleware(app)
    _setup_cors(app)
    _setup_routers(app)

    return app


def _setup_middleware(app: FastAPI) -> None:
    """Configure all middleware components with detailed logging."""
    logger.info(
        "Configuring FastAPI application",
        extra={
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION,
            "debug_mode": settings.DEBUG,
            "docs_enabled": settings.DEBUG,
        },
    )

    # === ENHANCED MIDDLEWARE STACK (Order Matters!) ===

    # 1. API Versioning - Handle API versions early
    from user_service.app.middleware.api.versioning import APIVersioningMiddleware

    app.add_middleware(
        APIVersioningMiddleware,
        default_version="1.0",
        supported_versions=["1.0", "1.1"],
    )
    logger.info("API versioning middleware configured")

    # 2. Rate Limiting - Protect against abuse
    try:
        from user_service.app.middleware.security.rate_limiting import (
            UserServiceRateLimiter,
            UserServiceRateLimitingMiddleware,
        )

        rate_limiter = UserServiceRateLimiter()
        app.add_middleware(UserServiceRateLimitingMiddleware, rate_limiter=rate_limiter)
        logger.info("Rate limiting middleware configured")
    except Exception as e:
        logger.warning(f"Rate limiting unavailable: {e}")

    # 3. Request Validation - Early validation and security
    from user_service.app.middleware.security.validation_middleware import (
        setup_user_request_validation_middleware,
    )

    setup_user_request_validation_middleware(app)
    logger.info("Request validation middleware configured")

    # 4. Authentication - JWT token validation and user context
    from user_service.app.api.dependencies import jwt_handler
    from user_service.app.middleware.auth.auth_middleware import (
        setup_user_auth_middleware,
    )

    setup_user_auth_middleware(app, jwt_handler=jwt_handler)
    logger.info("Authentication middleware configured")

    # 5. Role Authorization - Role-based access control
    from user_service.app.middleware.auth.role_middleware import (
        setup_user_role_authorization_middleware,
    )

    setup_user_role_authorization_middleware(app)
    logger.info("Role authorization middleware configured")

    # 6. Error Handling - Centralized exception handling
    from user_service.app.middleware.error.error_handler import (
        setup_user_error_handling,
    )

    setup_user_error_handling(app)
    logger.info("Error handling middleware configured")


def _setup_cors(app: FastAPI) -> None:
    """Configure CORS settings with logging."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
    )

    logger.info(
        "CORS middleware configured",
        extra={
            "allowed_origins": len(settings.CORS_ORIGINS),
            "credentials_allowed": settings.CORS_CREDENTIALS,
        },
    )


def _setup_routers(app: FastAPI) -> None:
    """Configure all application routers with detailed logging."""
    routers_info: list[dict[str, Any]] = []

    # Health router
    app.include_router(health_router, tags=["Health"])
    routers_info.append({"router": "health", "prefix": "", "tags": ["Health"]})

    # Authentication router
    app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])
    routers_info.append(
        {"router": "auth", "prefix": "/api/v1", "tags": ["Authentication"]}
    )

    # User management router
    app.include_router(user_router, prefix="/api/v1/users", tags=["User Management"])
    routers_info.append(
        {"router": "user", "prefix": "/api/v1/users", "tags": ["User Management"]}
    )

    # Profile router
    app.include_router(profile_router, prefix="/api/v1", tags=["User Profiles"])
    routers_info.append(
        {"router": "profile", "prefix": "/api/v1", "tags": ["User Profiles"]}
    )

    # Address router
    app.include_router(address_router, prefix="/api/v1", tags=["User Addresses"])
    routers_info.append(
        {"router": "address", "prefix": "/api/v1", "tags": ["User Addresses"]}
    )

    # Permissions API for cross-service permission checking
    app.include_router(permissions_router, prefix="/api/v1", tags=["Permissions"])
    routers_info.append(
        {"router": "permissions", "prefix": "/api/v1", "tags": ["Permissions"]}
    )

    # Add management routes
    try:
        from user_service.app.api.v1.management import router as management_router

        app.include_router(management_router)
        routers_info.append(
            {
                "router": "management",
                "prefix": "/user-service",
                "tags": ["user-service-management"],
            }
        )
        logger.info("Management routes registered at /user-service/*")
    except ImportError as e:
        logger.warning(f"Management routes not available: {e}")

    logger.info(
        "API routes configured",
        extra={"total_routers": len(routers_info), "routers": routers_info},
    )


app = create_app()
