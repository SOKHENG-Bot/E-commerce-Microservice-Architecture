import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, List, Optional

from app.api.v1.health import router as health_router
from app.api.v1.orders import router as orders_router
from app.core.database import database_manager
from app.core.events import close_events, init_events
from app.core.setting import get_settings
from app.middleware.auth import (
    setup_order_auth_middleware,
    setup_order_role_authorization_middleware,
)
from app.middleware.error import setup_order_error_handling
from app.middleware.security import setup_order_request_validation_middleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add the project root to the path so we can import shared modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.utils.logging import setup_order_logging as setup_logging
except ImportError:
    # Fallback for when running from different contexts
    import logging
    from typing import List, Optional

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


settings = get_settings()

# Enhanced logging with production features
environment = os.getenv("ENVIRONMENT", "development").lower()
enable_file_logging = environment in ["production", "staging"]

logger = setup_logging(
    "order_service",
    log_level=settings.LOG_LEVEL,
    enable_file_logging=enable_file_logging,
    enable_performance_logging=True,
)


# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_start = time.time()

    try:
        logger.info(
            "Starting order service initialization",
            extra={
                "environment": environment,
                "debug_mode": settings.DEBUG,
                "file_logging_enabled": enable_file_logging,
                "service_version": settings.APP_VERSION,
            },
        )

        # Database initialization
        db_start = time.time()
        await database_manager.create_tables()
        db_duration = int((time.time() - db_start) * 1000)
        logger.info(
            "Database initialization completed", extra={"duration_ms": db_duration}
        )

        # Event publisher initialization
        event_start = time.time()
        await init_events()
        event_duration = int((time.time() - event_start) * 1000)
        logger.info("Event publisher started", extra={"duration_ms": event_duration})

        # Event consumer initialization
        consumer_start = time.time()
        from order_service.app.core.events import get_event_producer
        from order_service.app.events.consumers import OrderEventConsumer

        event_producer = get_event_producer()
        if event_producer is None:
            logger.warning(
                "Event producer not available, skipping event consumer initialization"
            )
        else:
            # Create a session for the consumer
            async with database_manager.async_session_maker() as consumer_session:
                consumer = OrderEventConsumer(consumer_session, event_producer)
                # Store consumer in app state for shutdown
                app.state.event_consumer = consumer
                await consumer.start()

        consumer_duration = int((time.time() - consumer_start) * 1000)
        logger.info(
            "Event consumer initialization completed",
            extra={"duration_ms": consumer_duration},
        )

        total_startup = int((time.time() - startup_start) * 1000)
        logger.info(
            "Order service started successfully",
            extra={
                "total_startup_duration_ms": total_startup,
                "database_init_ms": db_duration,
                "event_publisher_init_ms": event_duration,
                "event_consumer_init_ms": consumer_duration,
            },
        )

    except Exception as e:
        logger.error(
            "Failed to start order service",
            exc_info=True,
            extra={
                "startup_duration_ms": int((time.time() - startup_start) * 1000),
                "error_type": type(e).__name__,
            },
        )
        raise

    yield

    shutdown_start = time.time()
    try:
        logger.info("Starting order service shutdown")

        # Stop event consumer
        if hasattr(app.state, "event_consumer"):
            await app.state.event_consumer.stop()

        await close_events()

        shutdown_duration = int((time.time() - shutdown_start) * 1000)
        logger.info(
            "Order service shutdown completed",
            extra={"shutdown_duration_ms": shutdown_duration},
        )

    except Exception as e:
        logger.error(
            "Error during order service shutdown",
            exc_info=True,
            extra={
                "shutdown_duration_ms": int((time.time() - shutdown_start) * 1000),
                "error_type": type(e).__name__,
            },
        )
        raise


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # === ENHANCED MIDDLEWARE STACK (Order Matters!) ===

    # 1. CORS middleware
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

    # 1. Request Validation middleware (must come first)
    setup_order_request_validation_middleware(app)
    logger.info("✅ Request validation middleware configured")

    # 2. Authentication middleware (must come before logging)
    setup_order_auth_middleware(app)
    logger.info("✅ Authentication middleware configured")

    # 3. Role Authorization middleware (must come after auth)
    setup_order_role_authorization_middleware(app)
    logger.info("✅ Role authorization middleware configured")

    # 4. Error handling (must come after all middleware)
    setup_order_error_handling(app)
    logger.info("✅ Error handling middleware configured")

    logger.info(
        "Configuring FastAPI application",
        extra={
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION,
            "debug_mode": settings.DEBUG,
            "docs_enabled": settings.DEBUG,
        },
    )

    # Include routers with enhanced logging
    routers_info: list[dict[str, Any]] = []

    app.include_router(health_router, tags=["Health"])
    routers_info.append({"router": "health", "prefix": "", "tags": ["Health"]})

    app.include_router(orders_router, prefix="/api/v1", tags=["Order Management"])
    routers_info.append(
        {"router": "orders", "prefix": "/api/v1", "tags": ["Order Management"]}
    )

    logger.info(
        "API routes configured",
        extra={"total_routers": len(routers_info), "routers": routers_info},
    )

    return app


app = create_app()
