"""Database configuration for Order Service"""

from typing import Any, AsyncGenerator, Dict

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..models.base import OrderServiceBase
from .setting import get_settings


class OrderServiceDatabaseManager:
    """Custom database manager for Order Service with optimized settings."""

    def __init__(
        self,
        database_url: str,
        echo: bool = False,
        pool_size: int = 20,
        max_overflow: int = 40,
    ) -> None:
        # Order Service specific database configuration
        engine_kwargs: Dict[str, Any] = {
            "echo": echo,
            "future": True,
            "pool_size": pool_size,
            "max_overflow": max_overflow,
        }

        if "sqlite" in database_url:
            # SQLite configuration for development
            engine_kwargs["connect_args"] = {
                "timeout": 60,
                "check_same_thread": False,
            }
        else:
            # PostgreSQL configuration optimized for Order Service
            engine_kwargs.update(
                {
                    "pool_timeout": 45,
                    "pool_recycle": 3600,  # 1 hour recycle for order sessions
                    "pool_pre_ping": True,
                    "pool_reset_on_return": "commit",
                    "connect_args": {
                        "command_timeout": 30,
                        "server_settings": {
                            "jit": "off",
                            # Note: shared_preload_libraries must be set at server startup
                            # "shared_preload_libraries": "pg_stat_statements",
                        },
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
        """Create all Order Service database tables."""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(OrderServiceBase.metadata.create_all, checkfirst=True)

    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session for Order Service."""
        async with self.async_session_maker() as session:
            yield session

    async def close(self) -> None:
        """Properly close the Order Service database engine and connections."""
        await self.async_engine.dispose()


# Initialize Order Service database manager
settings = get_settings()
database_manager = OrderServiceDatabaseManager(
    database_url=settings.ORDER_DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency for FastAPI using Order Service database manager"""
    async for session in database_manager.get_async_session():
        yield session
