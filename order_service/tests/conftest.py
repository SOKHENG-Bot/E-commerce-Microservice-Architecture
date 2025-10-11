"""
Pytest configuration and fixtures for Order Service tests.
"""

import asyncio
import os
from typing import Any, AsyncGenerator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Set up test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["TEST_DATABASE_URL"] = "sqlite+aiosqlite:///test.db"

# Import order service components
from order_service.app.core.database import database_manager
from order_service.app.core.setting import get_settings
from order_service.app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """Get test settings."""
    return get_settings()


@pytest.fixture(scope="session")
async def test_database_manager():
    """Create test database manager."""
    settings = get_settings()
    test_db_url = settings.TEST_DATABASE_URL or "sqlite+aiosqlite:///test.db"

    # Create tables
    await database_manager.create_tables()

    yield database_manager

    # Cleanup
    await database_manager.close()
    try:
        os.remove("test.db")
    except FileNotFoundError:
        pass


@pytest.fixture
async def db_session(test_database_manager) -> AsyncGenerator[Any, None]:
    """Create a test database session."""
    async with test_database_manager.async_session_maker() as session:
        yield session


@pytest.fixture
def test_app() -> FastAPI:
    """Get test FastAPI application."""
    return app


@pytest.fixture
def client(test_app) -> TestClient:
    """FastAPI test client fixture."""
    return TestClient(test_app)


@pytest.fixture
def mock_request():
    """Mock FastAPI Request object."""
    from unittest.mock import Mock

    from fastapi import Request

    mock_req = Mock(spec=Request)
    mock_req.state = Mock()
    mock_req.headers = {}
    mock_req.cookies = {}
    mock_req.url = Mock()
    mock_req.url.path = "/test"
    mock_req.method = "GET"
    return mock_req


@pytest.fixture
def mock_response():
    """Mock FastAPI Response object."""
    from unittest.mock import Mock

    from starlette.responses import Response

    mock_resp = Mock(spec=Response)
    mock_resp.status_code = 200
    mock_resp.headers = {}
    return mock_resp


@pytest.fixture
def mock_call_next():
    """Mock call_next function for middleware testing."""

    async def call_next(request):
        from starlette.responses import Response

        return Response("OK", status_code=200)

    return call_next


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "user_id": "123",
        "email": "test@example.com",
        "username": "testuser",
        "role": "user",
        "roles": ["user"],
        "permissions": [],
    }


@pytest.fixture
def sample_token_data():
    """Sample JWT token data."""
    return {
        "user_id": "123",
        "email": "test@example.com",
        "username": "testuser",
        "roles": ["user"],
        "permissions": [],
        "exp": 9999999999,
        "iat": 1000000000,
        "token_type": "access",
    }
