"""
Pytest configuration and fixtures for user service tests.
"""

import asyncio
import os
from typing import Any, AsyncGenerator

import pytest
from fastapi.testclient import TestClient

# Set up test database before importing anything else
os.environ["TEST_DATABASE_URL"] = "sqlite+aiosqlite:///test.db"
os.environ["USER_DATABASE_URL"] = "sqlite+aiosqlite:///test.db"

# Import all models FIRST to ensure they're registered with SQLAlchemy
from user_service.app.core.database import UserServiceDatabaseManager
from user_service.app.core.settings import get_settings
from user_service.app.main import app
from user_service.app.models.address import Address  # noqa: F401
from user_service.app.models.profile import Profile  # noqa: F401
from user_service.app.models.user import (  # noqa: F401
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_database_manager(request):
    """Create test database manager with SQLite file database."""
    import asyncio

    settings = get_settings()
    test_db_url = settings.TEST_DATABASE_URL or "sqlite+aiosqlite:///test.db"

    # Create test database manager
    manager = UserServiceDatabaseManager(database_url=test_db_url, echo=False)

    # Create tables
    asyncio.run(manager.create_tables())

    # Set the global database_manager for tests
    import user_service.app.core.database as db_module

    db_module.database_manager = manager

    def cleanup():
        asyncio.run(manager.close())
        # Clean up the test database file
        import os

        try:
            os.remove("test.db")
        except FileNotFoundError:
            pass
        db_module.database_manager = None

    request.addfinalizer(cleanup)

    return manager


@pytest.fixture(scope="session")
async def test_session_maker(test_database_manager: UserServiceDatabaseManager) -> Any:
    """Create test session maker."""
    return test_database_manager.async_session_maker


@pytest.fixture
async def db_session(test_session_maker: Any) -> AsyncGenerator[Any, None]:
    """Create a test database session with proper cleanup."""
    async with test_session_maker() as session:
        yield session


@pytest.fixture
def client(test_database_manager) -> TestClient:
    """FastAPI test client fixture."""
    return TestClient(app)
