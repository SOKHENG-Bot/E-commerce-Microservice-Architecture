from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.app.events.event_producers import UserEventProducer
from user_service.app.models.user import User
from user_service.app.schemas.user import UserUpdate
from user_service.app.services.user_service import UserService


class TestUserService:
    """Comprehensive unit tests for UserService methods."""

    @pytest.fixture
    def mock_session(self):
        """Mock async session."""
        return Mock(spec=AsyncSession)

    @pytest.fixture
    def mock_event_publisher(self):
        """Mock event publisher."""
        return Mock(spec=UserEventProducer)

    @pytest.fixture
    def user_service(self, mock_session, mock_event_publisher):
        """Create UserService instance with mocked dependencies."""
        return UserService(mock_session, mock_event_publisher)

    @pytest.fixture
    def sample_user(self):
        """Sample user data for testing."""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        user.username = "testuser"
        user.phone_number = "+1234567890"
        user.is_active = True
        user.is_verified = True
        user.date_joined = datetime(2023, 1, 1, tzinfo=timezone.utc)
        user.last_login = datetime(2023, 1, 1, tzinfo=timezone.utc)
        user.created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        user.updated_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        user.roles = []
        user.profile = None  # No profile for this test
        user.addresses = []  # No addresses for this test
        return user

    @pytest.fixture
    def inactive_user(self):
        """Sample inactive user data for testing reactivation."""
        user = Mock(spec=User)
        user.id = 2
        user.email = "inactive@example.com"
        user.username = "inactiveuser"
        user.phone_number = "+1234567890"
        user.is_active = False
        user.is_verified = True
        user.date_joined = datetime(2023, 1, 1, tzinfo=timezone.utc)
        user.last_login = datetime(2023, 1, 1, tzinfo=timezone.utc)
        user.roles = []
        return user

    @pytest.fixture
    def sample_user_update(self):
        """Sample user update data."""
        return UserUpdate(username="updateduser", phone="+0987654321")

    # Tests for get_current_user_profile method
    @pytest.mark.asyncio
    async def test_get_current_user_profile_success(self, user_service, sample_user):
        """Test successful retrieval of current user profile."""
        # Arrange
        user_service.user_repository.query_info = AsyncMock(return_value=sample_user)

        # Act
        result = await user_service.get_current_user_profile(sample_user)

        # Assert
        assert result == sample_user
        user_service.user_repository.query_info.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_current_user_profile_user_not_found(
        self, user_service, sample_user
    ):
        """Test get_current_user_profile when user is not found."""
        # Arrange
        user_service.user_repository.query_info = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await user_service.get_current_user_profile(sample_user)

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail
        user_service.user_repository.query_info.assert_called_once_with(1)

    # Tests for update_current_user_profile method
    @pytest.mark.asyncio
    async def test_update_current_user_profile_success(
        self, user_service, sample_user, sample_user_update
    ):
        """Test successful user profile update."""
        # Arrange
        updated_user = Mock(spec=User)
        updated_user.id = 1
        updated_user.email = "test@example.com"
        updated_user.username = "updateduser"
        updated_user.phone_number = "+0987654321"
        updated_user.is_active = True

        user_service.user_repository.query_id = AsyncMock(return_value=sample_user)
        user_service.user_repository.update = AsyncMock(return_value=updated_user)
        user_service.event_publisher.publish_user_updated = AsyncMock()

        # Act
        result = await user_service.update_current_user_profile(
            sample_user, sample_user_update
        )

        # Assert
        assert result == updated_user
        user_service.user_repository.query_id.assert_called_once_with(1)
        user_service.user_repository.update.assert_called_once()
        user_service.event_publisher.publish_user_updated.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_current_user_profile_user_not_found(
        self, user_service, sample_user, sample_user_update
    ):
        """Test update_current_user_profile when user is not found."""
        # Arrange
        user_service.user_repository.query_id = AsyncMock(return_value=None)
        user_service.user_repository.update = AsyncMock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await user_service.update_current_user_profile(
                sample_user, sample_user_update
            )

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail
        user_service.user_repository.query_id.assert_called_once_with(1)
        user_service.user_repository.update.assert_not_called()

    # Tests for deactivate_account method
    @pytest.mark.asyncio
    async def test_deactivate_account_success(self, user_service, sample_user):
        """Test successful account deactivation."""
        # Arrange
        deactivated_user = Mock(spec=User)
        deactivated_user.id = 1
        deactivated_user.email = "test@example.com"
        deactivated_user.is_active = False

        user_service.user_repository.query_id = AsyncMock(return_value=sample_user)
        user_service.user_repository.update = AsyncMock(return_value=deactivated_user)
        user_service.event_publisher.publish_user_deactivated = AsyncMock()

        # Act
        result = await user_service.deactivate_account(sample_user)

        # Assert
        assert result == deactivated_user
        user_service.user_repository.query_id.assert_called_once_with(1)
        user_service.user_repository.update.assert_called_once()
        user_service.event_publisher.publish_user_deactivated.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_account_user_not_found(self, user_service, sample_user):
        """Test deactivate_account when user is not found."""
        # Arrange
        user_service.user_repository.query_id = AsyncMock(return_value=None)
        user_service.user_repository.update = AsyncMock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await user_service.deactivate_account(sample_user)

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail
        user_service.user_repository.query_id.assert_called_once_with(1)
        user_service.user_repository.update.assert_not_called()

    # Tests for reactivate_account method
    @pytest.mark.asyncio
    async def test_reactivate_account_success(self, user_service, inactive_user):
        """Test successful account reactivation."""
        # Arrange
        reactivated_user = Mock(spec=User)
        reactivated_user.id = 2
        reactivated_user.email = "inactive@example.com"
        reactivated_user.is_active = True

        user_service.user_repository.query_email = AsyncMock(return_value=inactive_user)
        user_service.user_repository.update = AsyncMock(return_value=reactivated_user)
        user_service.event_publisher.publish_user_reactivated = AsyncMock()

        # Act
        result = await user_service.reactivate_account("inactive@example.com")

        # Assert
        assert result == reactivated_user
        user_service.user_repository.query_email.assert_called_once_with(
            "inactive@example.com"
        )
        user_service.user_repository.update.assert_called_once()
        user_service.event_publisher.publish_user_reactivated.assert_called_once()

    @pytest.mark.asyncio
    async def test_reactivate_account_user_not_found(self, user_service):
        """Test reactivate_account when user is not found."""
        # Arrange
        user_service.user_repository.query_email = AsyncMock(return_value=None)
        user_service.user_repository.update = AsyncMock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await user_service.reactivate_account("nonexistent@example.com")

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail
        user_service.user_repository.query_email.assert_called_once_with(
            "nonexistent@example.com"
        )
        user_service.user_repository.update.assert_not_called()

    # Tests for get_account_information method
    @pytest.mark.asyncio
    async def test_get_account_information_success(self, user_service, sample_user):
        """Test successful retrieval of user account information."""
        # Arrange
        user_service.user_repository.query_id = AsyncMock(return_value=sample_user)

        # Act
        result = await user_service.get_account_information(sample_user)

        # Assert
        assert isinstance(result, dict)
        assert result["user_id"] == "1"
        assert result["email"] == "test@example.com"
        assert result["is_active"]
        user_service.user_repository.query_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_account_information_user_not_found(
        self, user_service, sample_user
    ):
        """Test get_account_information when user is not found."""
        # Arrange
        user_service.user_repository.query_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await user_service.get_account_information(sample_user)

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail
        user_service.user_repository.query_id.assert_called_once_with(1)

    # Tests for delete_account method
    @pytest.mark.asyncio
    async def test_delete_account_success(self, user_service, sample_user):
        """Test successful account deletion."""
        # Arrange
        user_service.user_repository.query_id = AsyncMock(return_value=sample_user)
        user_service.event_publisher.publish_user_deleted = AsyncMock()
        user_service.user_repository.delete = AsyncMock()

        # Act
        result = await user_service.delete_account(sample_user)

        # Assert
        assert result == {"message": "Account has been permanently deleted."}
        user_service.user_repository.query_id.assert_called_once_with(1)
        user_service.event_publisher.publish_user_deleted.assert_called_once()
        user_service.user_repository.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_account_user_not_found(self, user_service, sample_user):
        """Test delete_account when user is not found."""
        # Arrange
        user_service.user_repository.query_id = AsyncMock(return_value=None)
        user_service.user_repository.delete = AsyncMock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await user_service.delete_account(sample_user)

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail
        user_service.user_repository.query_id.assert_called_once_with(1)
        user_service.user_repository.delete.assert_not_called()

    # Tests for get_user_by_id_for_admin method
    @pytest.mark.asyncio
    async def test_get_user_by_id_for_admin_success(self, user_service, sample_user):
        """Test successful retrieval of user profile by admin."""
        # Arrange
        user_service.user_repository.query_info = AsyncMock(return_value=sample_user)

        # Act
        result = await user_service.get_user_by_id_for_admin(1)

        # Assert
        assert result == sample_user
        user_service.user_repository.query_info.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_user_by_id_for_admin_user_not_found(self, user_service):
        """Test get_user_by_id_for_admin when user is not found."""
        # Arrange
        user_service.user_repository.query_info = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await user_service.get_user_by_id_for_admin(999)

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail
        user_service.user_repository.query_info.assert_called_once_with(999)
