"""
Notification Service FastAPI Application
========================================

Main application entry point for the Notification Service microservice.
Handles email/SMS notifications, template management, and bulk messaging.
Provides REST API endpoints with     # 2. Authentication - JWT token validation and user context
    setup_notification_auth_middleware(app)e middleware stack for security,
monitoring, and performance optimization.
"""

import asyncio
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# API routers
from .api.v1.bulk_notifications import router as bulk_notifications_router
from .api.v1.health import router as health_router
from .api.v1.notifications import router as notifications_router
from .api.v1.templates import router as templates_router

# Core components
from .core.database import database_manager
from .core.events import close_events, init_events
from .core.settings import get_settings

# Event consumers
from .events.consumers import NotificationEventConsumer

# Middleware
from .middleware.auth.auth_middleware import setup_notification_auth_middleware
from .middleware.auth.role_middleware import (
    setup_notification_role_authorization_middleware,
)
from .middleware.error import setup_error_middleware
from .middleware.validation import setup_validation_middleware

# Project path setup
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Settings and environment
settings = get_settings()
environment = os.getenv("ENVIRONMENT", "development").lower()
enable_file_logging = environment in ["production", "staging"]

# Global event consumer reference for shutdown
_event_consumer: Optional[NotificationEventConsumer] = None


def _setup_application_logging():
    """Setup application logging with fallback support."""
    try:
        from .utils.logging import setup_notification_logging as setup_logging
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
        "notification_service",
        log_level=getattr(settings, "LOG_LEVEL", "INFO"),
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
        "Starting notification service initialization",
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
        "Notification service started successfully",
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

    session = database_manager.async_session_maker()
    consumer = NotificationEventConsumer(session)

    # Start consumer in background to avoid blocking startup
    asyncio.create_task(_start_event_consumer_async(consumer, app))

    duration = int((time.time() - start_time) * 1000)
    logger.info(
        "Event consumer initialization started (non-blocking)",
        extra={"duration_ms": duration},
    )
    return duration


async def _start_event_consumer_async(
    consumer: NotificationEventConsumer, app: FastAPI
) -> None:
    """Start event consumer asynchronously without blocking startup."""
    global _event_consumer
    try:
        await consumer.start()
        _event_consumer = consumer
        app.state.event_consumer = consumer  # Keep for backward compatibility
        logger.info("Event consumer started successfully")
    except Exception as e:
        logger.warning(f"Event consumer failed to start, continuing without it: {e}")
        # Don't set the global reference if it fails


async def _handle_startup_error(startup_start: float, error: Exception) -> None:
    """Handle startup errors with proper logging."""
    logger.error(
        "Failed to start notification service",
        exc_info=True,
        extra={
            "startup_duration_ms": int((time.time() - startup_start) * 1000),
            "error_type": type(error).__name__,
        },
    )


async def _shutdown_services() -> None:
    """Shutdown all application services gracefully."""
    global _event_consumer
    shutdown_start = time.time()

    try:
        logger.info("Starting notification service shutdown")

        # Stop event consumer
        if _event_consumer:
            await _event_consumer.stop()
            _event_consumer = None

        await close_events()

        shutdown_duration = int((time.time() - shutdown_start) * 1000)
        logger.info(
            "Notification service shutdown completed",
            extra={"shutdown_duration_ms": shutdown_duration},
        )

    except Exception as e:
        logger.error(
            "Error during notification service shutdown",
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

    # 1. Request Validation - Early validation and security
    setup_validation_middleware(app)
    logger.info("Request validation middleware configured")

    # 2. Authentication - JWT token validation and user context
    setup_notification_auth_middleware(
        app,
        exclude_paths=[
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
            "/api/v1/templates",  # Allow template management without auth for development
            "/api/v1/notifications/send",
        ],
    )
    logger.info("Authentication middleware configured")

    # 3. Role Authorization - Role-based access control
    setup_notification_role_authorization_middleware(app)
    logger.info("Role authorization middleware configured")

    # 4. Error Handling - Centralized exception handling
    setup_error_middleware(app, debug_mode=settings.DEBUG)
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

    # Notifications router
    app.include_router(notifications_router, prefix="/api/v1", tags=["Notifications"])
    routers_info.append(
        {"router": "notifications", "prefix": "/api/v1", "tags": ["Notifications"]}
    )

    # Templates router
    app.include_router(templates_router, prefix="/api/v1", tags=["Templates"])
    routers_info.append(
        {"router": "templates", "prefix": "/api/v1", "tags": ["Templates"]}
    )

    # Bulk notifications router
    app.include_router(
        bulk_notifications_router, prefix="/api/v1", tags=["Bulk Notifications"]
    )
    routers_info.append(
        {
            "router": "bulk_notifications",
            "prefix": "/api/v1",
            "tags": ["Bulk Notifications"],
        }
    )

    logger.info(
        "API routes configured",
        extra={"total_routers": len(routers_info), "routers": routers_info},
    )


app = create_app()
