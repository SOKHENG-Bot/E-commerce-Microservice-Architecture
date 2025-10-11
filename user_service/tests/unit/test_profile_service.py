"""
Unit tests for ProfileService
"""

from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.app.events.event_producers import UserEventProducer
from user_service.app.models.profile import GenderEnum, Profile
from user_service.app.models.user import User
from user_service.app.schemas.profile import ProfileCreate, ProfileUpdate
from user_service.app.services.profile_service import ProfileService


class TestProfileService:
    """Comprehensive unit tests for ProfileService methods."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_event_publisher(self):
        """Mock event publisher."""
        return AsyncMock(spec=UserEventProducer)

    @pytest.fixture
    def profile_service(self, mock_session, mock_event_publisher):
        """ProfileService instance with mocked dependencies."""
        return ProfileService(mock_session, mock_event_publisher)

    @pytest.fixture
    def sample_user(self):
        """Sample user for testing."""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def sample_profile(self):
        """Sample profile for testing."""
        profile = Mock(spec=Profile)
        profile.id = 1
        profile.user_id = 1
        profile.avatar_url = "https://example.com/avatar.jpg"
        profile.date_of_birth = date(1990, 1, 1)
        profile.gender = GenderEnum.MALE
        profile.bio = "Test bio"
        profile.preferences = {"theme": "dark"}
        return profile

    @pytest.fixture
    def sample_profile_create(self):
        """Sample profile create data."""
        return ProfileCreate(
            avatar_url="https://example.com/avatar.jpg",
            date_of_birth=date(1990, 1, 1),
            gender=GenderEnum.MALE,
            bio="Test bio",
            preferences={"theme": "dark"},
        )

    @pytest.fixture
    def sample_profile_update(self):
        """Sample profile update data."""
        return ProfileUpdate(
            bio="Updated bio",
            preferences={"theme": "light"},
        )

    # Tests for get_profile method
    @pytest.mark.asyncio
    async def test_get_profile_success(self, profile_service, sample_profile):
        """Test successful profile retrieval."""
        # Setup
        profile_service.profile_repository.get_profile = AsyncMock(
            return_value=sample_profile
        )

        # Execute
        result = await profile_service.get_profile(1)

        # Assert
        assert result == sample_profile
        profile_service.profile_repository.get_profile.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, profile_service):
        """Test profile retrieval when profile doesn't exist."""
        # Setup
        profile_service.profile_repository.get_profile = AsyncMock(return_value=None)

        # Execute
        result = await profile_service.get_profile(1)

        # Assert
        assert result is None
        profile_service.profile_repository.get_profile.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_profile_exception(self, profile_service):
        """Test profile retrieval when database exception occurs."""
        # Setup
        profile_service.profile_repository.get_profile = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Execute & Assert
        with pytest.raises(HTTPException) as exc_info:
            await profile_service.get_profile(1)

        assert exc_info.value.status_code == 500
        assert "Failed to retrieve profile" in exc_info.value.detail

    # Tests for create_profile method
    @pytest.mark.asyncio
    async def test_create_profile_success(
        self, profile_service, sample_user, sample_profile_create, sample_profile
    ):
        """Test successful profile creation."""
        # Setup
        profile_service.profile_repository.get_profile = AsyncMock(return_value=None)
        profile_service.profile_repository.create = AsyncMock(
            return_value=sample_profile
        )
        profile_service.event_publisher.publish_profile_created = AsyncMock()

        # Execute
        result = await profile_service.create_profile(
            sample_user, sample_profile_create
        )

        # Assert
        assert result == sample_profile
        profile_service.profile_repository.get_profile.assert_called_once_with(1)
        profile_service.profile_repository.create.assert_called_once()
        profile_service.event_publisher.publish_profile_created.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_profile_already_exists(
        self, profile_service, sample_user, sample_profile_create, sample_profile
    ):
        """Test profile creation when profile already exists."""
        # Setup
        profile_service.profile_repository.get_profile = AsyncMock(
            return_value=sample_profile
        )

        # Execute & Assert
        with pytest.raises(HTTPException) as exc_info:
            await profile_service.create_profile(sample_user, sample_profile_create)

        assert exc_info.value.status_code == 400
        assert "Profile already exists" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_profile_exception(
        self, profile_service, sample_user, sample_profile_create
    ):
        """Test profile creation when database exception occurs."""
        # Setup
        profile_service.profile_repository.get_profile = AsyncMock(return_value=None)
        profile_service.profile_repository.create = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Execute & Assert
        with pytest.raises(HTTPException) as exc_info:
            await profile_service.create_profile(sample_user, sample_profile_create)

        assert exc_info.value.status_code == 500
        assert "Failed to create profile" in exc_info.value.detail

    # Tests for update_profile method
    @pytest.mark.asyncio
    async def test_update_profile_success(
        self, profile_service, sample_user, sample_profile, sample_profile_update
    ):
        """Test successful profile update."""
        # Setup
        profile_service.profile_repository.get_profile = AsyncMock(
            return_value=sample_profile
        )
        profile_service.profile_repository.update = AsyncMock(
            return_value=sample_profile
        )
        profile_service.event_publisher.publish_user_updated = AsyncMock()

        # Execute
        result = await profile_service.update_profile(
            sample_user, sample_profile_update
        )

        # Assert
        assert result == sample_profile
        profile_service.profile_repository.get_profile.assert_called_once_with(1)
        profile_service.profile_repository.update.assert_called_once()
        profile_service.event_publisher.publish_user_updated.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_profile_user_not_authenticated(
        self, profile_service, sample_profile_update
    ):
        """Test profile update when user is not authenticated."""
        # Execute & Assert
        with pytest.raises(HTTPException) as exc_info:
            await profile_service.update_profile(None, sample_profile_update)

        assert exc_info.value.status_code == 401
        assert "User is not authenticated" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_profile_not_found(
        self, profile_service, sample_user, sample_profile_update
    ):
        """Test profile update when profile doesn't exist."""
        # Setup
        profile_service.profile_repository.get_profile = AsyncMock(return_value=None)

        # Execute & Assert
        with pytest.raises(HTTPException) as exc_info:
            await profile_service.update_profile(sample_user, sample_profile_update)

        assert exc_info.value.status_code == 404
        assert "Profile not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_profile_no_changes(
        self, profile_service, sample_user, sample_profile
    ):
        """Test profile update when no changes are made."""
        # Setup
        profile_service.profile_repository.get_profile = AsyncMock(
            return_value=sample_profile
        )
        profile_service.profile_repository.update = AsyncMock(
            return_value=sample_profile
        )
        profile_service.event_publisher.publish_user_updated = AsyncMock()

        # Empty update
        update_data = ProfileUpdate()

        # Execute
        result = await profile_service.update_profile(sample_user, update_data)

        # Assert
        assert result == sample_profile
        profile_service.profile_repository.update.assert_not_called()
        profile_service.event_publisher.publish_user_updated.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_profile_exception(
        self, profile_service, sample_user, sample_profile, sample_profile_update
    ):
        """Test profile update when database exception occurs."""
        # Setup
        profile_service.profile_repository.get_profile = AsyncMock(
            return_value=sample_profile
        )
        profile_service.profile_repository.update = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Execute & Assert
        with pytest.raises(HTTPException) as exc_info:
            await profile_service.update_profile(sample_user, sample_profile_update)

        assert exc_info.value.status_code == 500
        assert "Failed to update profile" in exc_info.value.detail

    # Tests for delete_profile method
    @pytest.mark.asyncio
    async def test_delete_profile_success(
        self, profile_service, sample_user, sample_profile
    ):
        """Test successful profile deletion."""
        # Setup
        profile_service.profile_repository.get_profile = AsyncMock(
            return_value=sample_profile
        )
        profile_service.profile_repository.delete = AsyncMock()
        profile_service.event_publisher.publish_user_updated = AsyncMock()

        # Execute
        result = await profile_service.delete_profile(sample_user)

        # Assert
        assert result == {"message": "Profile deleted successfully."}
        profile_service.profile_repository.get_profile.assert_called_once_with(1)
        profile_service.profile_repository.delete.assert_called_once()
        profile_service.event_publisher.publish_user_updated.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_profile_user_not_authenticated(self, profile_service):
        """Test profile deletion when user is not authenticated."""
        # Execute & Assert
        with pytest.raises(HTTPException) as exc_info:
            await profile_service.delete_profile(None)

        assert exc_info.value.status_code == 401
        assert "User is not authenticated" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_profile_not_found(self, profile_service, sample_user):
        """Test profile deletion when profile doesn't exist."""
        # Setup
        profile_service.profile_repository.get_profile = AsyncMock(return_value=None)

        # Execute & Assert
        with pytest.raises(HTTPException) as exc_info:
            await profile_service.delete_profile(sample_user)

        assert exc_info.value.status_code == 404
        assert "Profile not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_profile_exception(
        self, profile_service, sample_user, sample_profile
    ):
        """Test profile deletion when database exception occurs."""
        # Setup
        profile_service.profile_repository.get_profile = AsyncMock(
            return_value=sample_profile
        )
        profile_service.profile_repository.delete = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Execute & Assert
        with pytest.raises(HTTPException) as exc_info:
            await profile_service.delete_profile(sample_user)

        assert exc_info.value.status_code == 500
        assert "Failed to delete profile" in exc_info.value.detail

    # Tests for calculate_profile_completeness method
    @pytest.mark.asyncio
    async def test_calculate_profile_completeness_full(
        self, profile_service, sample_profile
    ):
        """Test profile completeness calculation with all fields filled."""
        # Setup
        profile_service.profile_repository.get_profile = AsyncMock(
            return_value=sample_profile
        )

        # Execute
        result = await profile_service.calculate_profile_completeness(1)

        # Assert
        assert result == {
            "completeness": 100,
            "total_fields": 5,
            "completed_fields": 5,
        }

    @pytest.mark.asyncio
    async def test_calculate_profile_completeness_partial(self, profile_service):
        """Test profile completeness calculation with some fields filled."""
        # Setup
        partial_profile = Mock(spec=Profile)
        partial_profile.avatar_url = "https://example.com/avatar.jpg"
        partial_profile.date_of_birth = None
        partial_profile.gender = GenderEnum.MALE
        partial_profile.bio = ""
        partial_profile.preferences = {}

        profile_service.profile_repository.get_profile = AsyncMock(
            return_value=partial_profile
        )

        # Execute
        result = await profile_service.calculate_profile_completeness(1)

        # Assert
        assert result == {
            "completeness": 40,  # 2 out of 5 fields completed
            "total_fields": 5,
            "completed_fields": 2,
        }

    @pytest.mark.asyncio
    async def test_calculate_profile_completeness_empty(self, profile_service):
        """Test profile completeness calculation with no fields filled."""
        # Setup
        empty_profile = Mock(spec=Profile)
        empty_profile.avatar_url = None
        empty_profile.date_of_birth = None
        empty_profile.gender = None
        empty_profile.bio = None
        empty_profile.preferences = None

        profile_service.profile_repository.get_profile = AsyncMock(
            return_value=empty_profile
        )

        # Execute
        result = await profile_service.calculate_profile_completeness(1)

        # Assert
        assert result == {
            "completeness": 0,
            "total_fields": 5,
            "completed_fields": 0,
        }

    @pytest.mark.asyncio
    async def test_calculate_profile_completeness_no_profile(self, profile_service):
        """Test profile completeness calculation when profile doesn't exist."""
        # Setup
        profile_service.profile_repository.get_profile = AsyncMock(return_value=None)

        # Execute
        result = await profile_service.calculate_profile_completeness(1)

        # Assert
        assert result == {
            "completeness": 0,
            "total_fields": 5,
            "completed_fields": 0,
        }

    @pytest.mark.asyncio
    async def test_calculate_profile_completeness_exception(self, profile_service):
        """Test profile completeness calculation when exception occurs."""
        # Setup
        profile_service.profile_repository.get_profile = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Execute
        result = await profile_service.calculate_profile_completeness(1)

        # Assert - Should return default values on error
        assert result == {
            "completeness": 0,
            "total_fields": 5,
            "completed_fields": 0,
        }
