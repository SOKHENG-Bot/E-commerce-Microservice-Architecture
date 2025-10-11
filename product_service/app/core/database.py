from typing import Any, AsyncGenerator, Dict

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..models.base import ProductServiceBase
from ..utils.logging import setup_product_logging as setup_logging
from .setting import get_settings

# Setup structured logging for database operations
logger = setup_logging("product_service.database", log_level=get_settings().LOG_LEVEL)


class ProductServiceDatabaseManager:
    """Custom database manager for Product Service with optimized settings."""

    def __init__(self, database_url: str, echo: bool = False) -> None:
        logger.info(
            "Initializing Product Service database manager",
            extra={
                "operation": "database_manager_init",
                "database_url": database_url.replace(
                    "postgresql+asyncpg://", "postgresql://"
                ).split("@")[0]
                + "@***",  # Mask credentials
                "echo": echo,
                "service": "product_service",
                "event_type": "database_manager_initialization",
            },
        )

        # Product Service specific database configuration
        engine_kwargs: Dict[str, Any] = {
            "echo": echo,
            "future": True,
        }

        if "sqlite" in database_url:
            # SQLite configuration for development
            engine_kwargs["connect_args"] = {
                "timeout": 60,
                "check_same_thread": False,
            }
            logger.info(
                "Configured SQLite database settings",
                extra={
                    "database_type": "sqlite",
                    "timeout": 60,
                    "service": "product_service",
                },
            )
        else:
            # PostgreSQL configuration optimized for Product Service
            engine_kwargs.update(
                {
                    "pool_size": 25,  # Product Service specific pool size
                    "max_overflow": 50,  # Overflow for product catalog peaks
                    "pool_timeout": 45,
                    "pool_recycle": 3600,  # 1 hour recycle for product sessions
                    "pool_pre_ping": True,
                    "pool_reset_on_return": "commit",
                    "connect_args": {
                        "command_timeout": 30,
                        # Disable prepared statements to avoid shared_preload_libraries requirement
                        "prepared_statement_cache_size": 0,
                    },
                }
            )
            logger.info(
                "Configured PostgreSQL database settings",
                extra={
                    "database_type": "postgresql",
                    "pool_size": 25,
                    "max_overflow": 50,
                    "pool_timeout": 45,
                    "pool_recycle": 3600,
                    "service": "product_service",
                },
            )

        self.async_engine = create_async_engine(database_url, **engine_kwargs)
        self.async_session_maker = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

        logger.info(
            "Product Service database manager initialized successfully",
            extra={
                "operation": "database_manager_init_complete",
                "service": "product_service",
                "event_type": "database_manager_ready",
            },
        )

    async def create_tables(self) -> None:
        """Create all Product Service database tables."""
        try:
            async with self.async_engine.begin() as conn:
                await conn.run_sync(
                    ProductServiceBase.metadata.create_all, checkfirst=True
                )
            logger.info(
                "Database tables created successfully",
                extra={
                    "operation": "create_tables",
                    "service": "product_service",
                    "event_type": "database_tables_created",
                },
            )
        except Exception as e:
            # Log the error but don't fail - tables might already exist from another instance
            logger.warning(
                "Database table creation failed",
                extra={
                    "operation": "create_tables",
                    "error": str(e),
                    "service": "product_service",
                    "event_type": "database_table_creation_failed",
                },
            )
            # Continue anyway - the tables should exist

    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session for Product Service."""
        async with self.async_session_maker() as session:
            yield session

    async def close(self) -> None:
        """Properly close the Product Service database engine and connections."""
        logger.info(
            "Closing Product Service database connections",
            extra={
                "operation": "database_close",
                "service": "product_service",
                "event_type": "database_shutdown",
            },
        )
        await self.async_engine.dispose()
        logger.info(
            "Product Service database connections closed",
            extra={
                "operation": "database_close_complete",
                "service": "product_service",
                "event_type": "database_shutdown_complete",
            },
        )


# Initialize Product Service database manager (REQUIRED)
settings = get_settings()
if not settings.PRODUCT_DATABASE_URL:
    error_msg = (
        "PRODUCT_DATABASE_URL is required for Product Service but not configured"
    )
    logger.error(
        error_msg,
        extra={
            "operation": "global_database_init",
            "database_configured": False,
            "service": "product_service",
            "event_type": "database_config_missing",
        },
    )
    raise ValueError(error_msg)

database_manager = ProductServiceDatabaseManager(
    database_url=settings.PRODUCT_DATABASE_URL, echo=settings.DEBUG
)
logger.info(
    "Product Service database manager initialized globally",
    extra={
        "operation": "global_database_init",
        "database_configured": True,
        "debug_mode": settings.DEBUG,
        "service": "product_service",
        "event_type": "database_global_init",
    },
)


# Dependency injection function for FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    async for session in database_manager.get_async_session():
        yield session
