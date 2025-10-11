from typing import Any, AsyncGenerator, Dict

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..models.base import NotificationServiceBase
from .settings import get_settings


class NotificationServiceDatabaseManager:
    """Custom database manager for Notification Service with optimized settings."""

    def __init__(self, database_url: str, echo: bool = False) -> None:
        # Notification Service specific database configuration
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
        else:
            # PostgreSQL configuration optimized for Notification Service
            engine_kwargs.update(
                {
                    "pool_size": 25,  # Notification Service specific pool size
                    "max_overflow": 50,  # Overflow for notification bursts
                    "pool_timeout": 45,
                    "pool_recycle": 3600,  # 1 hour recycle for notification sessions
                    "pool_pre_ping": True,
                    "pool_reset_on_return": "commit",
                    "connect_args": {
                        "command_timeout": 30,
                        # Removed server_settings to avoid runtime parameter issues
                    },
                }
            )

        self.async_engine = create_async_engine(database_url, **engine_kwargs)
        self.async_session_maker = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    async def create_tables(self) -> None:
        """Create all Notification Service database tables."""
        try:
            async with self.async_engine.begin() as conn:
                await conn.run_sync(
                    NotificationServiceBase.metadata.create_all, checkfirst=True
                )
        except Exception as e:
            # Log the error but don't fail - tables might already exist from another instance
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Table creation failed (might already exist): {e}")
            # Continue anyway - the tables should exist

    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session for Notification Service."""
        async with self.async_session_maker() as session:
            yield session

    async def close(self) -> None:
        """Properly close the Notification Service database engine and connections."""
        await self.async_engine.dispose()


# Initialize Notification Service database manager
settings = get_settings()
database_manager = NotificationServiceDatabaseManager(
    database_url=settings.NOTIFICATION_DATABASE_URL, echo=settings.DEBUG
)


async def create_tables():
    """Create all notification service tables using service-specific database manager"""
    await database_manager.create_tables()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency for FastAPI using service-specific database manager"""
    async for session in database_manager.get_async_session():
        yield session


# For backward compatibility, expose the engine
engine = database_manager.async_engine
