"""
Unit tests for PermissionService
"""

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.app.models.user import Permission, Role, User
from user_service.app.services.permission_service import PermissionService


class TestPermissionService:
    """Comprehensive unit tests for PermissionService methods."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def permission_service(self, mock_session):
        """PermissionService instance with mocked session."""
        return PermissionService(mock_session)

    @pytest.fixture
    def sample_user(self):
        """Sample user for testing."""
        user = Mock(spec=User)
        user.id = 1
        user.roles = []
        return user

    @pytest.fixture
    def sample_role(self):
        """Sample role for testing."""
        role = Mock(spec=Role)
        role.id = 1
        role.name = "admin"
        role.permissions = []
        return role

    @pytest.fixture
    def sample_permission(self):
        """Sample permission for testing."""
        permission = Mock(spec=Permission)
        permission.id = 1
        permission.name = "read_users"
        return permission

    # Tests for has_permission method
    @pytest.mark.asyncio
    async def test_has_permission_success(
        self,
        permission_service,
        mock_session,
        sample_user,
        sample_role,
        sample_permission,
    ):
        """Test successful permission check when user has the permission."""
        # Setup
        sample_role.permissions = [sample_permission]
        sample_user.roles = [sample_role]

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result

        # Execute
        result = await permission_service.has_permission(1, "read_users")

        # Assert
        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_has_permission_user_not_found(
        self, permission_service, mock_session
    ):
        """Test permission check when user is not found."""
        # Setup
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        result = await permission_service.has_permission(999, "read_users")

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_has_permission_no_permission(
        self, permission_service, mock_session, sample_user, sample_role
    ):
        """Test permission check when user doesn't have the required permission."""
        # Setup
        sample_role.permissions = []  # No permissions
        sample_user.roles = [sample_role]

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result

        # Execute
        result = await permission_service.has_permission(1, "read_users")

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_has_permission_no_roles(
        self, permission_service, mock_session, sample_user
    ):
        """Test permission check when user has no roles."""
        # Setup
        sample_user.roles = []  # No roles

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result

        # Execute
        result = await permission_service.has_permission(1, "read_users")

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_has_permission_exception(self, permission_service, mock_session):
        """Test permission check when database exception occurs."""
        # Setup
        mock_session.execute.side_effect = Exception("Database error")

        # Execute
        result = await permission_service.has_permission(1, "read_users")

        # Assert
        assert result is False

    # Tests for get_user_permissions method
    @pytest.mark.asyncio
    async def test_get_user_permissions_success(
        self,
        permission_service,
        mock_session,
        sample_user,
        sample_role,
        sample_permission,
    ):
        """Test successful retrieval of user permissions."""
        # Setup
        sample_role.permissions = [sample_permission]
        sample_user.roles = [sample_role]

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result

        # Execute
        result = await permission_service.get_user_permissions(1)

        # Assert
        assert result == ["read_users"]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_permissions_user_not_found(
        self, permission_service, mock_session
    ):
        """Test permission retrieval when user is not found."""
        # Setup
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        result = await permission_service.get_user_permissions(999)

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_permissions_no_permissions(
        self, permission_service, mock_session, sample_user, sample_role
    ):
        """Test permission retrieval when user has no permissions."""
        # Setup
        sample_role.permissions = []  # No permissions
        sample_user.roles = [sample_role]

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result

        # Execute
        result = await permission_service.get_user_permissions(1)

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_permissions_multiple_permissions(
        self, permission_service, mock_session, sample_user, sample_role
    ):
        """Test permission retrieval with multiple permissions and roles."""
        # Setup
        perm1 = Mock(spec=Permission)
        perm1.name = "read_users"
        perm2 = Mock(spec=Permission)
        perm2.name = "write_users"
        perm3 = Mock(spec=Permission)
        perm3.name = "delete_users"

        role1 = Mock(spec=Role)
        role1.permissions = [perm1, perm2]
        role2 = Mock(spec=Role)
        role2.permissions = [perm2, perm3]  # Overlapping permission

        sample_user.roles = [role1, role2]

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result

        # Execute
        result = await permission_service.get_user_permissions(1)

        # Assert
        assert set(result) == {"read_users", "write_users", "delete_users"}

    @pytest.mark.asyncio
    async def test_get_user_permissions_exception(
        self, permission_service, mock_session
    ):
        """Test permission retrieval when database exception occurs."""
        # Setup
        mock_session.execute.side_effect = Exception("Database error")

        # Execute
        result = await permission_service.get_user_permissions(1)

        # Assert
        assert result == []

    # Tests for get_user_roles method
    @pytest.mark.asyncio
    async def test_get_user_roles_success(
        self, permission_service, mock_session, sample_user, sample_role
    ):
        """Test successful retrieval of user roles."""
        # Setup
        sample_user.roles = [sample_role]

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result

        # Execute
        result = await permission_service.get_user_roles(1)

        # Assert
        assert result == ["admin"]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_roles_user_not_found(
        self, permission_service, mock_session
    ):
        """Test role retrieval when user is not found."""
        # Setup
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        result = await permission_service.get_user_roles(999)

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_roles_no_roles(
        self, permission_service, mock_session, sample_user
    ):
        """Test role retrieval when user has no roles."""
        # Setup
        sample_user.roles = []  # No roles

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result

        # Execute
        result = await permission_service.get_user_roles(1)

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_roles_multiple_roles(
        self, permission_service, mock_session, sample_user
    ):
        """Test role retrieval with multiple roles."""
        # Setup
        role1 = Mock(spec=Role)
        role1.name = "admin"
        role2 = Mock(spec=Role)
        role2.name = "moderator"

        sample_user.roles = [role1, role2]

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result

        # Execute
        result = await permission_service.get_user_roles(1)

        # Assert
        assert result == ["admin", "moderator"]

    @pytest.mark.asyncio
    async def test_get_user_roles_exception(self, permission_service, mock_session):
        """Test role retrieval when database exception occurs."""
        # Setup
        mock_session.execute.side_effect = Exception("Database error")

        # Execute
        result = await permission_service.get_user_roles(1)

        # Assert
        assert result == []

    # Tests for assign_role_to_user method
    @pytest.mark.asyncio
    async def test_assign_role_to_user_success(
        self, permission_service, mock_session, sample_user, sample_role
    ):
        """Test successful role assignment to user."""
        # Setup
        sample_user.roles = []  # User starts with no roles

        user_result = Mock()
        user_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = user_result

        # Mock the role query
        role_result = Mock()
        role_result.scalar_one_or_none.return_value = sample_role
        mock_session.execute.side_effect = [user_result, role_result]

        # Execute
        result = await permission_service.assign_role_to_user(1, "admin")

        # Assert
        assert result is True
        assert sample_role in sample_user.roles
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_role_to_user_user_not_found(
        self, permission_service, mock_session
    ):
        """Test role assignment when user is not found."""
        # Setup
        user_result = Mock()
        user_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = user_result

        # Execute
        result = await permission_service.assign_role_to_user(999, "admin")

        # Assert
        assert result is False
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_assign_role_to_user_role_not_found(
        self, permission_service, mock_session, sample_user
    ):
        """Test role assignment when role is not found."""
        # Setup
        user_result = Mock()
        user_result.scalar_one_or_none.return_value = sample_user

        role_result = Mock()
        role_result.scalar_one_or_none.return_value = None

        mock_session.execute.side_effect = [user_result, role_result]

        # Execute
        result = await permission_service.assign_role_to_user(1, "nonexistent_role")

        # Assert
        assert result is False
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_assign_role_to_user_already_has_role(
        self, permission_service, mock_session, sample_user, sample_role
    ):
        """Test role assignment when user already has the role."""
        # Setup
        sample_user.roles = [sample_role]  # User already has the role

        user_result = Mock()
        user_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = user_result

        # Mock the role query
        role_result = Mock()
        role_result.scalar_one_or_none.return_value = sample_role
        mock_session.execute.side_effect = [user_result, role_result]

        # Execute
        result = await permission_service.assign_role_to_user(1, "admin")

        # Assert
        assert result is True
        mock_session.commit.assert_not_called()  # No commit needed

    @pytest.mark.asyncio
    async def test_assign_role_to_user_exception(
        self, permission_service, mock_session
    ):
        """Test role assignment when database exception occurs."""
        # Setup
        mock_session.execute.side_effect = Exception("Database error")

        # Execute
        result = await permission_service.assign_role_to_user(1, "admin")

        # Assert
        assert result is False
        mock_session.rollback.assert_called_once()

    # Tests for remove_role_from_user method
    @pytest.mark.asyncio
    async def test_remove_role_from_user_success(
        self, permission_service, mock_session, sample_user, sample_role
    ):
        """Test successful role removal from user."""
        # Setup
        sample_user.roles = [sample_role]  # User has the role

        user_result = Mock()
        user_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = user_result

        # Execute
        result = await permission_service.remove_role_from_user(1, "admin")

        # Assert
        assert result is True
        assert sample_role not in sample_user.roles
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_role_from_user_user_not_found(
        self, permission_service, mock_session
    ):
        """Test role removal when user is not found."""
        # Setup
        user_result = Mock()
        user_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = user_result

        # Execute
        result = await permission_service.remove_role_from_user(999, "admin")

        # Assert
        assert result is False
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_role_from_user_role_not_assigned(
        self, permission_service, mock_session, sample_user
    ):
        """Test role removal when user doesn't have the role."""
        # Setup
        sample_user.roles = []  # User doesn't have the role

        user_result = Mock()
        user_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = user_result

        # Execute
        result = await permission_service.remove_role_from_user(1, "admin")

        # Assert
        assert result is True  # Still returns True as operation succeeded
        mock_session.commit.assert_not_called()  # No changes to commit

    @pytest.mark.asyncio
    async def test_remove_role_from_user_exception(
        self, permission_service, mock_session
    ):
        """Test role removal when database exception occurs."""
        # Setup
        mock_session.execute.side_effect = Exception("Database error")

        # Execute
        result = await permission_service.remove_role_from_user(1, "admin")

        # Assert
        assert result is False
        mock_session.rollback.assert_called_once()
