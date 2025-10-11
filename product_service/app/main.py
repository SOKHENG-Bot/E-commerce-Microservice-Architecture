"""
Product Service FastAPI Application
==================================

Main application entry point for the Product Service microservice.
Handles product management, categories, and inventory functionality.
Provides REST API endpoints with comprehensive middleware stack for security,
logging, monitoring, and cross-service communication.
"""

import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, List, Optional

# API routers
from app.api.v1.categories import router as categories_router
from app.api.v1.health import router as health_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.performance import router as performance_router
from app.api.v1.products import router as products_router

# Core imports
from app.core.database import database_manager
from app.core.event_management import close_events, init_events
from app.core.setting import get_settings

# Middleware imports
from app.middleware.api.versioning import APIVersioningMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Constants
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB

# Add the project root to the path so we can import shared modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
settings = get_settings()
environment = os.getenv("ENVIRONMENT", "development").lower()
enable_file_logging = environment in ["production", "staging"]


def _setup_application_logging():
    """Setup application logging with fallback support."""
    try:
        from app.utils.logging import setup_product_logging as setup_logging
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
        "product_service",
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
        "Starting product service initialization",
        extra={
            "environment": environment,
            "debug_mode": settings.DEBUG,
            "file_logging_enabled": enable_file_logging,
            "service_version": settings.APP_VERSION,
        },
    )

    # Initialize event publisher (with Kafka check)
    event_duration, event_publisher_initialized = await _init_event_publisher()

    # Initialize database (required)
    db_duration = await _init_database()

    # Initialize event consumer (only if event publisher was initialized)
    consumer_duration = 0
    if event_publisher_initialized:
        try:
            consumer_duration = await _init_event_consumer(app)
        except Exception as e:
            logger.warning(
                "Event consumer initialization failed, continuing without events",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
    else:
        logger.info(
            "Skipping event consumer initialization (event publisher not available)"
        )

    # Log successful startup
    total_startup = int((time.time() - startup_start) * 1000)
    logger.info(
        "Product service started successfully",
        extra={
            "total_startup_duration_ms": total_startup,
            "database_init_ms": db_duration,
            "event_publisher_init_ms": event_duration,
            "event_consumer_init_ms": consumer_duration,
        },
    )


async def _init_event_publisher() -> tuple[int, bool]:
    """Initialize event publisher and return duration in ms and success status."""
    start_time = time.time()

    try:
        # Quick check if Kafka is available
        import socket

        kafka_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        if ":" in kafka_servers:
            kafka_host, kafka_port = kafka_servers.split(":")
            kafka_port = int(kafka_port)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            result = sock.connect_ex((kafka_host, kafka_port))
            sock.close()

            kafka_available = result == 0
        else:
            kafka_available = False

        if kafka_available:
            await init_events()
            duration = int((time.time() - start_time) * 1000)
            logger.info("Event publisher started", extra={"duration_ms": duration})
            return duration, True
        else:
            logger.warning(
                "Kafka not available, skipping event publisher initialization"
            )
            return 0, False

    except Exception as e:
        logger.warning(
            f"Event publisher initialization failed: {e}, continuing without events"
        )
        return int((time.time() - start_time) * 1000), False


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

    from app.core.event_management import get_event_producer

    from product_service.app.events.event_consumers import ProductEventConsumer

    async with database_manager.async_session_maker() as consumer_session:
        event_producer = get_event_producer()
        if event_producer is None:
            raise RuntimeError("Event producer not initialized")
        consumer = ProductEventConsumer(consumer_session, event_producer)
        app.state.event_consumer = consumer
        await consumer.start()

    duration = int((time.time() - start_time) * 1000)
    logger.info("Event consumer started", extra={"duration_ms": duration})
    return duration


async def _handle_startup_error(startup_start: float, error: Exception) -> None:
    """Handle startup errors with proper logging."""
    logger.error(
        "Failed to start product service",
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
        logger.info("Starting product service shutdown")

        # Stop event consumer
        if (
            hasattr(app.state, "event_consumer")
            and app.state.event_consumer is not None
        ):
            await app.state.event_consumer.stop()

        await close_events()

        shutdown_duration = int((time.time() - shutdown_start) * 1000)
        logger.info(
            "Product service shutdown completed",
            extra={"shutdown_duration_ms": shutdown_duration},
        )

    except Exception as e:
        logger.error(
            "Error during product service shutdown",
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

    # 1. API Versioning middleware
    app.add_middleware(APIVersioningMiddleware)
    logger.info("API versioning middleware configured")

    # 2. Request validation middleware (early validation and security)
    from app.middleware.common.validation_middleware import (
        setup_request_validation_middleware,
    )

    setup_request_validation_middleware(app)
    logger.info("Request validation middleware configured")

    # 3. Authentication middleware (must come after validation)
    from app.middleware.auth.auth_middleware import setup_product_auth_middleware

    setup_product_auth_middleware(app)
    logger.info("Authentication middleware configured")

    # 4. Role authorization middleware (must come after authentication)
    from app.middleware.auth.role_middleware import setup_role_authorization_middleware

    setup_role_authorization_middleware(app)
    logger.info("Role authorization middleware configured")

    # 5. Error handling setup
    from app.middleware.error.error_handler import setup_product_error_handling

    setup_product_error_handling(app)
    logger.info("Error handling middleware configured")

    # 6. Caching middleware (must come after error handling)
    from app.middleware.common.caching import setup_product_caching_middleware

    app.state.cache_middleware = setup_product_caching_middleware(
        app,
        max_cache_size=1000,  # Configurable cache size
        enabled=True,  # Enable caching by default
    )
    logger.info("Caching middleware configured")


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

    # Products router
    app.include_router(products_router, prefix="/api/v1", tags=["Product Management"])
    routers_info.append(
        {"router": "products", "prefix": "/api/v1", "tags": ["Product Management"]}
    )

    # Categories router
    app.include_router(
        categories_router, prefix="/api/v1", tags=["Category Management"]
    )
    routers_info.append(
        {"router": "categories", "prefix": "/api/v1", "tags": ["Category Management"]}
    )

    # Inventory router
    app.include_router(
        inventory_router, prefix="/api/v1", tags=["Inventory Management"]
    )
    routers_info.append(
        {"router": "inventory", "prefix": "/api/v1", "tags": ["Inventory Management"]}
    )

    # Performance monitoring router
    app.include_router(
        performance_router, prefix="/api/v1/monitoring", tags=["Performance Monitoring"]
    )
    routers_info.append(
        {
            "router": "performance",
            "prefix": "/api/v1/monitoring",
            "tags": ["Performance Monitoring"],
        }
    )

    logger.info(
        "API routes configured",
        extra={"total_routers": len(routers_info), "routers": routers_info},
    )


app = create_app()
