"""
Pytest configuration and fixtures for user service tests.
"""

import asyncio
import os
from typing import Any, AsyncGenerator

import pytest
from fastapi.testclient import TestClient

# Set up test environment variables before importing anything else
os.environ.setdefault("APP_NAME", "User Service Test")
os.environ.setdefault("APP_VERSION", "1.0.0")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SERVICE_NAME", "user-service")
os.environ.setdefault("USER_SERVICE_URL", "http://localhost:8000")
os.environ.setdefault("USER_SERVICE_HEALTH", "/health")
os.environ.setdefault("USER_DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("TEST_DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("POSTGRES_DB", "user_service_test")
os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
os.environ.setdefault("KAFKA_GROUP_ID", "user-service-test")
os.environ.setdefault("KAFKA_TOPIC_USER_EVENTS", "user-events-test")
os.environ.setdefault("KAFKA_TOPIC_USER_REGISTRATION", "user-registration-test")
os.environ.setdefault("KAFKA_TOPIC_USER_LOGIN", "user-login-test")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_REQUESTS", "100")
os.environ.setdefault("RATE_LIMIT_WINDOW", "3600")
os.environ.setdefault("RATE_LIMIT_PER_USER_REQUESTS", "50")
os.environ.setdefault("RATE_LIMIT_PER_USER_WINDOW", "3600")
# SMTP settings (optional for tests)
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_PORT", "587")
os.environ.setdefault("SMTP_USERNAME", "test@example.com")
os.environ.setdefault("SMTP_PASSWORD", "test-password")
os.environ.setdefault("SMTP_FROM_EMAIL", "test@example.com")
os.environ.setdefault(
    "CORS_ORIGINS", '["http://localhost:3000", "http://localhost:8080"]'
)
os.environ.setdefault("CORS_CREDENTIALS", "true")
os.environ.setdefault("CORS_METHODS", '["GET", "POST", "PUT", "DELETE", "OPTIONS"]')
os.environ.setdefault("CORS_HEADERS", '["*"]')
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("ENABLE_ACCESS_LOGS", "false")

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
