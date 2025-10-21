import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from user_service.app.api.v1.addresses import address_router
from user_service.app.api.v1.auth import router as auth_router
from user_service.app.api.v1.health import router as health_router
from user_service.app.api.v1.profiles import router as profile_router
from user_service.app.api.v1.users import router as user_router
from user_service.app.core.database import database_manager
from user_service.app.core.event_management import close_events, init_events
from user_service.app.core.settings import get_settings
from user_service.app.events.event_consumers import UserEventConsumer
from user_service.app.middleware.auth.auth_middleware import (
    setup_user_auth_middleware,
)
from user_service.app.middleware.auth.role_middleware import (
    setup_user_role_authorization_middleware,
)
from user_service.app.middleware.error.error_handler import (
    setup_user_error_handling,
)
from user_service.app.middleware.security.rate_limiting import (
    UserServiceRateLimiter,
    UserServiceRateLimitingMiddleware,
)
from user_service.app.middleware.security.validation_middleware import (
    setup_user_request_validation_middleware,
)

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

settings = get_settings()
environment = os.getenv("ENVIRONMENT", "development").lower()
enable_file_logging = environment in ["production", "staging"]


def _setup_application_logging():
    """Setup application logging with fallback support."""
    try:
        from app.utils.logging import setup_user_logging as setup_logging
    except ImportError:

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown."""

    try:
        await _initialize_services(app)
    except Exception as e:
        await _handle_startup_error(e)
        raise

    yield
    await _shutdown_services()


async def _initialize_services(app: FastAPI) -> None:
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

    await _init_event_publisher()
    await _init_database()
    await _init_event_consumer(app)

    logger.info("User service started successfully")


async def _init_event_publisher() -> int:
    """Initialize event publisher and return duration in ms."""

    await init_events()
    logger.info("Event publisher started")
    return 0


async def _init_database() -> int:
    """Initialize database and return duration in ms."""

    await database_manager.create_tables()
    logger.info("Database initialization completed")
    return 0


async def _init_event_consumer(app: FastAPI) -> int:
    """Initialize event consumer and return duration in ms."""

    async with database_manager.async_session_maker() as consumer_session:
        consumer = UserEventConsumer(consumer_session)
        app.state.event_consumer = consumer
        await consumer.start()

    logger.info("Event consumer started")
    return 0


async def _handle_startup_error(error: Exception) -> None:
    """Handle startup errors with proper logging."""

    logger.error(
        "Failed to start user service",
        exc_info=True,
        extra={
            "error_type": type(error).__name__,
        },
    )


async def _shutdown_services() -> None:
    """Shutdown all application services gracefully."""

    try:
        logger.info("Starting user service shutdown")

        if hasattr(app.state, "event_consumer"):
            await app.state.event_consumer.stop()

        await close_events()
        logger.info("User service shutdown completed")

    except Exception as e:
        logger.error(
            "Error during user service shutdown",
            exc_info=True,
            extra={
                "error_type": type(e).__name__,
            },
        )
        raise


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

    try:
        rate_limiter = UserServiceRateLimiter()
        app.add_middleware(UserServiceRateLimitingMiddleware, rate_limiter=rate_limiter)
        logger.info("Rate limiting middleware configured")
    except Exception as e:
        logger.warning(f"Rate limiting unavailable: {e}")

    setup_user_request_validation_middleware(app)
    logger.info("Request validation middleware configured")

    setup_user_auth_middleware(
        app,
        exclude_paths=[
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/auth/verify-email-token",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
        ],
    )
    logger.info("Authentication middleware configured")

    setup_user_role_authorization_middleware(app)
    logger.info("Role authorization middleware configured")

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

    app.include_router(health_router, tags=["Health"])
    routers_info.append({"router": "health", "prefix": "", "tags": ["Health"]})

    app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])
    routers_info.append(
        {"router": "auth", "prefix": "/api/v1", "tags": ["Authentication"]}
    )

    app.include_router(user_router, prefix="/api/v1/users", tags=["User Management"])
    routers_info.append(
        {"router": "user", "prefix": "/api/v1/users", "tags": ["User Management"]}
    )

    app.include_router(profile_router, prefix="/api/v1", tags=["User Profiles"])
    routers_info.append(
        {"router": "profile", "prefix": "/api/v1", "tags": ["User Profiles"]}
    )

    app.include_router(address_router, prefix="/api/v1", tags=["User Addresses"])
    routers_info.append(
        {"router": "address", "prefix": "/api/v1", "tags": ["User Addresses"]}
    )

    logger.info(
        "API routes configured",
        extra={"total_routers": len(routers_info), "routers": routers_info},
    )


app = create_app()
