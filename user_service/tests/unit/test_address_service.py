from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.app.models.address import Address, AddressTypeEnum
from user_service.app.models.user import User
from user_service.app.schemas.address import AddressCreate, AddressUpdate
from user_service.app.services.address_service import AddressService


class TestAddressService:
    """Comprehensive unit tests for AddressService methods."""

    @pytest.fixture
    def mock_session(self):
        """Mock async session."""
        return Mock(spec=AsyncSession)

    @pytest.fixture
    def mock_event_publisher(self):
        """Mock event publisher."""
        return Mock()

    @pytest.fixture
    def address_service(self, mock_session, mock_event_publisher):
        """Create AddressService instance with mocked dependencies."""
        return AddressService(mock_session, mock_event_publisher)

    @pytest.fixture
    def sample_user(self):
        """Sample user data for testing."""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        user.username = "testuser"
        return user

    @pytest.fixture
    def sample_address(self):
        """Sample address data for testing."""
        address = Mock(spec=Address)
        address.id = 1
        address.user_id = 1
        address.type = AddressTypeEnum.BILLING
        address.street_address = "123 Main St"
        address.apartment = "Apt 4B"
        address.city = "New York"
        address.state = "NY"
        address.postal_code = "10001"
        address.country = "USA"
        address.is_default = True
        return address

    @pytest.fixture
    def sample_address_create(self):
        """Sample address creation data."""
        return AddressCreate(
            type=AddressTypeEnum.BILLING,
            street_address="123 Main St",
            apartment="Apt 4B",
            city="New York",
            state="NY",
            postal_code="10001",
            country="USA",
            is_default=True,
        )

    @pytest.fixture
    def sample_address_update(self):
        """Sample address update data."""
        return AddressUpdate(
            street_address="456 Oak Ave", city="Los Angeles", is_default=False
        )

    # Tests for get_user_addresses method
    @pytest.mark.asyncio
    async def test_get_user_addresses_success(self, address_service, sample_address):
        """Test successful retrieval of user addresses."""
        # Arrange
        address_service.address_repository.get_addresses_by_user = AsyncMock(
            return_value=[sample_address]
        )

        # Act
        result = await address_service.get_user_addresses(1)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == sample_address
        address_service.address_repository.get_addresses_by_user.assert_called_once_with(
            1
        )

    # Tests for get_address_by_id method
    @pytest.mark.asyncio
    async def test_get_address_by_id_success(
        self, address_service, sample_address, sample_user
    ):
        """Test successful retrieval of address by ID."""
        # Arrange
        address_service.address_repository.get_address_by_id = AsyncMock(
            return_value=sample_address
        )

        # Act
        result = await address_service.get_address_by_id(1, 1)

        # Assert
        assert result == sample_address
        address_service.address_repository.get_address_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_address_by_id_not_found(self, address_service):
        """Test address retrieval when address not found."""
        # Arrange
        address_service.address_repository.get_address_by_id = AsyncMock(
            return_value=None
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await address_service.get_address_by_id(999, 1)

        assert exc_info.value.status_code == 404
        assert "Address not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_address_by_id_access_denied(
        self, address_service, sample_address
    ):
        """Test address retrieval when user doesn't own the address."""
        # Arrange
        sample_address.user_id = 2  # Different user
        address_service.address_repository.get_address_by_id = AsyncMock(
            return_value=sample_address
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await address_service.get_address_by_id(
                1, 1
            )  # User 1 trying to access address owned by user 2

        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail

    # Tests for create_address method
    @pytest.mark.asyncio
    async def test_create_address_success(
        self, address_service, sample_user, sample_address_create, sample_address
    ):
        """Test successful address creation."""
        # Arrange
        address_service.address_repository.unset_default_addresses = AsyncMock()
        address_service.address_repository.create = AsyncMock(
            return_value=sample_address
        )
        address_service.event_publisher.publish_address_created = AsyncMock()

        # Mock the Address constructor
        with patch(
            "user_service.app.services.address_service.Address"
        ) as mock_address_class:
            mock_address_instance = Mock()
            mock_address_instance.id = 1
            mock_address_class.return_value = mock_address_instance

            # Act
            result = await address_service.create_address(
                sample_user, sample_address_create
            )

            # Assert
            assert result == sample_address
            address_service.address_repository.unset_default_addresses.assert_called_once_with(
                1, AddressTypeEnum.BILLING
            )
            address_service.address_repository.create.assert_called_once()
            address_service.event_publisher.publish_address_created.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_address_non_default(
        self, address_service, sample_user, sample_address
    ):
        """Test address creation when not setting as default."""
        # Arrange
        create_data = AddressCreate(
            type=AddressTypeEnum.SHIPPING,
            street_address="456 Work St",
            city="Boston",
            state="MA",
            postal_code="02101",
            country="USA",
            is_default=False,
        )

        address_service.address_repository.unset_default_addresses = AsyncMock()
        address_service.address_repository.create = AsyncMock(
            return_value=sample_address
        )
        address_service.event_publisher.publish_address_created = AsyncMock()

        with patch(
            "user_service.app.services.address_service.Address"
        ) as mock_address_class:
            mock_address_instance = Mock()
            mock_address_class.return_value = mock_address_instance

            # Act
            result = await address_service.create_address(sample_user, create_data)

            # Assert
            assert result == sample_address
            # Should not call unset_default_addresses for non-default address
            address_service.address_repository.unset_default_addresses.assert_not_called()
            address_service.address_repository.create.assert_called_once()
            address_service.event_publisher.publish_address_created.assert_called_once()

    # Tests for update_address method
    @pytest.mark.asyncio
    async def test_update_address_success(
        self, address_service, sample_user, sample_address, sample_address_update
    ):
        """Test successful address update."""
        # Arrange
        address_service.address_repository.get_address_by_id = AsyncMock(
            return_value=sample_address
        )
        address_service.address_repository.unset_default_addresses = AsyncMock()
        address_service.address_repository.update = AsyncMock(
            return_value=sample_address
        )
        address_service.event_publisher.publish_address_updated = AsyncMock()

        # Act
        result = await address_service.update_address(
            1, sample_user, sample_address_update
        )

        # Assert
        assert result == sample_address
        address_service.address_repository.get_address_by_id.assert_called_once_with(1)
        address_service.address_repository.update.assert_called_once()
        address_service.event_publisher.publish_address_updated.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_address_not_found(
        self, address_service, sample_user, sample_address_update
    ):
        """Test address update when address not found."""
        # Arrange
        address_service.address_repository.get_address_by_id = AsyncMock(
            return_value=None
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await address_service.update_address(
                999, sample_user, sample_address_update
            )

        assert exc_info.value.status_code == 404
        assert "Address not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_address_access_denied(
        self, address_service, sample_user, sample_address_update, sample_address
    ):
        """Test address update when user doesn't own the address."""
        # Arrange
        sample_address.user_id = 2  # Different user
        address_service.address_repository.get_address_by_id = AsyncMock(
            return_value=sample_address
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await address_service.update_address(1, sample_user, sample_address_update)

        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_address_not_authenticated(
        self, address_service, sample_address_update
    ):
        """Test address update when user is not authenticated."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await address_service.update_address(1, None, sample_address_update)

        assert exc_info.value.status_code == 401
        assert "User is not authenticated" in exc_info.value.detail

    # Tests for delete_address method
    @pytest.mark.asyncio
    async def test_delete_address_success(
        self, address_service, sample_user, sample_address
    ):
        """Test successful address deletion."""
        # Arrange
        address_service.address_repository.get_address_by_id = AsyncMock(
            return_value=sample_address
        )
        address_service.address_repository.delete = AsyncMock()
        address_service.event_publisher.publish_address_deleted = AsyncMock()

        # Act
        result = await address_service.delete_address(1, sample_user)

        # Assert
        assert result == {"message": "Address deleted successfully."}
        address_service.address_repository.get_address_by_id.assert_called_once_with(1)
        address_service.address_repository.delete.assert_called_once()
        address_service.event_publisher.publish_address_deleted.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_address_not_found(self, address_service, sample_user):
        """Test address deletion when address not found."""
        # Arrange
        address_service.address_repository.get_address_by_id = AsyncMock(
            return_value=None
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await address_service.delete_address(999, sample_user)

        assert exc_info.value.status_code == 404
        assert "Address not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_address_access_denied(
        self, address_service, sample_user, sample_address
    ):
        """Test address deletion when user doesn't own the address."""
        # Arrange
        sample_address.user_id = 2  # Different user
        address_service.address_repository.get_address_by_id = AsyncMock(
            return_value=sample_address
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await address_service.delete_address(1, sample_user)

        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_address_not_authenticated(self, address_service):
        """Test address deletion when user is not authenticated."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await address_service.delete_address(1, None)

        assert exc_info.value.status_code == 401
        assert "User is not authenticated" in exc_info.value.detail

    # Tests for get_default_address method
    @pytest.mark.asyncio
    async def test_get_default_address_success(self, address_service, sample_address):
        """Test successful retrieval of default address."""
        # Arrange
        address_service.address_repository.get_default_address = AsyncMock(
            return_value=sample_address
        )

        # Act
        result = await address_service.get_default_address(1, AddressTypeEnum.BILLING)

        # Assert
        assert result == sample_address
        address_service.address_repository.get_default_address.assert_called_once_with(
            1, AddressTypeEnum.BILLING
        )

    @pytest.mark.asyncio
    async def test_get_default_address_not_found(self, address_service):
        """Test default address retrieval when no default exists."""
        # Arrange
        address_service.address_repository.get_default_address = AsyncMock(
            return_value=None
        )

        # Act
        result = await address_service.get_default_address(1, AddressTypeEnum.BILLING)

        # Assert
        assert result is None
        address_service.address_repository.get_default_address.assert_called_once_with(
            1, AddressTypeEnum.BILLING
        )

    # Tests for set_default_address method
    @pytest.mark.asyncio
    async def test_set_default_address_success(
        self, address_service, sample_user, sample_address
    ):
        """Test successful setting of default address."""
        # Arrange
        address_service.address_repository.get_address_by_id = AsyncMock(
            return_value=sample_address
        )
        address_service.address_repository.get_default_address = AsyncMock(
            return_value=None
        )
        address_service.address_repository.unset_default_addresses = AsyncMock()
        address_service.address_repository.update = AsyncMock(
            return_value=sample_address
        )
        address_service.event_publisher.publish_default_address_changed = AsyncMock()

        # Act
        result = await address_service.set_default_address(1, sample_user)

        # Assert
        assert result == sample_address
        address_service.address_repository.get_address_by_id.assert_called_once_with(1)
        address_service.address_repository.unset_default_addresses.assert_called_once_with(
            1, AddressTypeEnum.BILLING
        )
        address_service.address_repository.update.assert_called_once()
        address_service.event_publisher.publish_default_address_changed.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_default_address_not_found(self, address_service, sample_user):
        """Test setting default address when address not found."""
        # Arrange
        address_service.address_repository.get_address_by_id = AsyncMock(
            return_value=None
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await address_service.set_default_address(999, sample_user)

        assert exc_info.value.status_code == 404
        assert "Address not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_set_default_address_access_denied(
        self, address_service, sample_user, sample_address
    ):
        """Test setting default address when user doesn't own the address."""
        # Arrange
        sample_address.user_id = 2  # Different user
        address_service.address_repository.get_address_by_id = AsyncMock(
            return_value=sample_address
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await address_service.set_default_address(1, sample_user)

        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_set_default_address_not_authenticated(self, address_service):
        """Test setting default address when user is not authenticated."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await address_service.set_default_address(1, None)

        assert exc_info.value.status_code == 401
        assert "User is not authenticated" in exc_info.value.detail
