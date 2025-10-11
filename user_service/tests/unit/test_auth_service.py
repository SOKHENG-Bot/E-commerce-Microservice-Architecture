from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.app.models.user import User
from user_service.app.schemas.user import (
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    UserCreate,
)
from user_service.app.services.auth_service import AuthService


class TestAuthService:
    """Comprehensive unit tests for AuthService methods."""

    @pytest.fixture
    def mock_session(self):
        """Mock async session."""
        return Mock(spec=AsyncSession)

    @pytest.fixture
    def mock_event_publisher(self):
        """Mock event publisher."""
        return Mock()

    @pytest.fixture
    def auth_service(self, mock_session, mock_event_publisher):
        """Create AuthService instance with mocked dependencies."""
        return AuthService(mock_session, mock_event_publisher)

    @pytest.fixture
    def sample_user(self):
        """Sample user data for testing."""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        user.username = "testuser"
        user.password_hash = "hashed_password"
        user.is_active = True
        user.is_verified = True
        user.last_login = datetime(2023, 1, 1, tzinfo=timezone.utc)
        user.roles = []
        return user

    @pytest.fixture
    def sample_user_create(self):
        """Sample user creation data."""
        return UserCreate(
            email="newuser@example.com",
            password="StrongPass123!",
            username="newuser",
            phone_number="+1234567890",
        )

    @pytest.fixture
    def sample_login_request(self):
        """Sample login request data."""
        return LoginRequest(email="test@example.com", password="password123")

    # Tests for register_user method
    @pytest.mark.asyncio
    async def test_register_user_success(
        self, auth_service, sample_user_create, sample_user
    ):
        """Test successful user registration."""
        # Arrange
        auth_service.user_repository.query_email = AsyncMock(return_value=None)
        auth_service.session.execute = AsyncMock(
            return_value=Mock(scalars=Mock(first=Mock(return_value=Mock(name="USER"))))
        )
        auth_service.session.add = Mock()
        auth_service.session.flush = AsyncMock()
        auth_service.session.commit = AsyncMock()
        auth_service.session.refresh = AsyncMock()
        auth_service.notification_client.send_welcome_email = AsyncMock(
            return_value={"success": True}
        )
        auth_service.event_publisher.publish_user_created = AsyncMock()

        # Mock the User constructor
        with patch("user_service.app.services.auth_service.User") as mock_user_class:
            mock_user_instance = Mock()
            mock_user_instance.id = 1
            mock_user_instance.email = "newuser@example.com"
            mock_user_instance.username = "newuser"
            mock_user_class.return_value = mock_user_instance

            # Act
            result = await auth_service.register_user(sample_user_create)

            # Assert
            assert "verify_token" in result
            assert result["expires_in_minutes"] == "5"
            auth_service.user_repository.query_email.assert_called_once_with(
                "newuser@example.com"
            )
            auth_service.notification_client.send_welcome_email.assert_called_once()
            auth_service.event_publisher.publish_user_created.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_email_exists(
        self, auth_service, sample_user_create, sample_user
    ):
        """Test registration when email already exists."""
        # Arrange
        auth_service.user_repository.query_email = AsyncMock(return_value=sample_user)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.register_user(sample_user_create)

        assert exc_info.value.status_code == 400
        assert "Email already registered" in exc_info.value.detail

    # Tests for refresh_verify_email_token method
    @pytest.mark.asyncio
    async def test_refresh_verify_email_token_success(self, auth_service, sample_user):
        """Test successful email verification token refresh."""
        # Arrange
        sample_user.is_verified = False
        auth_service.user_repository.query_email = AsyncMock(return_value=sample_user)
        auth_service.notification_client.send_email_verification = AsyncMock(
            return_value={"success": True}
        )

        # Act
        result = await auth_service.refresh_verify_email_token("test@example.com")

        # Assert
        assert "verify_token" in result
        assert result["expires_in_minutes"] == "5"
        auth_service.user_repository.query_email.assert_called_once_with(
            "test@example.com"
        )
        auth_service.notification_client.send_email_verification.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_verify_email_token_user_not_found(self, auth_service):
        """Test refresh token when user not found."""
        # Arrange
        auth_service.user_repository.query_email = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_verify_email_token("nonexistent@example.com")

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_refresh_verify_email_token_already_verified(
        self, auth_service, sample_user
    ):
        """Test refresh token when email is already verified."""
        # Arrange
        sample_user.is_verified = True
        auth_service.user_repository.query_email = AsyncMock(return_value=sample_user)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_verify_email_token("test@example.com")

        assert exc_info.value.status_code == 400
        assert "Email is already verified" in exc_info.value.detail

    # Tests for verify_email_token method
    @pytest.mark.asyncio
    async def test_verify_email_token_success(self, auth_service, sample_user):
        """Test successful email token verification."""
        # Arrange
        sample_user.is_verified = False
        auth_service.user_repository.query_email = AsyncMock(return_value=sample_user)
        auth_service.user_repository.update = AsyncMock(return_value=sample_user)
        auth_service.event_publisher.publish_verify_email = AsyncMock()

        with patch("user_service.app.services.auth_service.jwt_handler") as mock_jwt:
            mock_payload = Mock()
            mock_payload.email = "test@example.com"
            mock_jwt.decode_token.return_value = mock_payload

            # Act
            result = await auth_service.verify_email_token("valid_token")

            # Assert
            assert result is True
            auth_service.user_repository.query_email.assert_called_once_with(
                "test@example.com"
            )
            auth_service.user_repository.update.assert_called_once()
            auth_service.event_publisher.publish_verify_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_email_token_invalid_token(self, auth_service):
        """Test email verification with invalid token."""
        # Arrange
        with patch("user_service.app.services.auth_service.jwt_handler") as mock_jwt:
            mock_payload = Mock()
            mock_payload.email = None
            mock_jwt.decode_token.return_value = mock_payload

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.verify_email_token("invalid_token")

            assert exc_info.value.status_code == 400
            assert "Invalid token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_email_token_user_not_found(self, auth_service):
        """Test email verification when user not found."""
        # Arrange
        auth_service.user_repository.query_email = AsyncMock(return_value=None)

        with patch("user_service.app.services.auth_service.jwt_handler") as mock_jwt:
            mock_payload = Mock()
            mock_payload.email = "nonexistent@example.com"
            mock_jwt.decode_token.return_value = mock_payload

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.verify_email_token("valid_token")

            assert exc_info.value.status_code == 404
            assert "User not found" in exc_info.value.detail

    # Tests for authenticate_user method
    @pytest.mark.asyncio
    async def test_authenticate_user_success(
        self, auth_service, sample_user, sample_login_request
    ):
        """Test successful user authentication."""
        # Arrange
        auth_service.user_repository.query_email = AsyncMock(return_value=sample_user)
        auth_service.user_repository.update = AsyncMock(return_value=sample_user)
        auth_service.event_publisher.publish_user_login = AsyncMock()

        mock_request = Mock(spec=Request)
        mock_request.headers = {"User-Agent": "Test Browser"}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"

        mock_response = Mock(spec=Response)
        mock_response.set_cookie = Mock()

        with (
            patch(
                "user_service.app.services.auth_service.SecurityUtils.verify_password",
                return_value=True,
            ),
            patch("user_service.app.services.auth_service.jwt_handler") as mock_jwt,
        ):
            mock_jwt.encode_token.return_value = "mock_access_token"

            # Act
            result = await auth_service.authenticate_user(
                sample_login_request, mock_request, mock_response
            )

            # Assert
            assert result == sample_user
            auth_service.user_repository.query_email.assert_called_once_with(
                "test@example.com"
            )
            auth_service.user_repository.update.assert_called_once()
            mock_response.set_cookie.assert_called_once()
            auth_service.event_publisher.publish_user_login.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_credentials(
        self, auth_service, sample_login_request
    ):
        """Test authentication with invalid credentials."""
        # Arrange
        auth_service.user_repository.query_email = AsyncMock(return_value=None)

        mock_request = Mock(spec=Request)
        mock_response = Mock(spec=Response)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.authenticate_user(
                sample_login_request, mock_request, mock_response
            )

        assert exc_info.value.status_code == 401
        assert "Invalid email or password" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive_account(
        self, auth_service, sample_user, sample_login_request
    ):
        """Test authentication with inactive account."""
        # Arrange
        sample_user.is_active = False
        auth_service.user_repository.query_email = AsyncMock(return_value=sample_user)

        mock_request = Mock(spec=Request)
        mock_response = Mock(spec=Response)

        with patch(
            "user_service.app.services.auth_service.SecurityUtils.verify_password",
            return_value=True,
        ):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.authenticate_user(
                    sample_login_request, mock_request, mock_response
                )

            assert exc_info.value.status_code == 403
            assert "User account is inactive" in exc_info.value.detail

    # Tests for forgot_password method
    @pytest.mark.asyncio
    async def test_forgot_password_success(self, auth_service, sample_user):
        """Test successful forgot password request."""
        # Arrange
        auth_service.user_repository.query_email = AsyncMock(return_value=sample_user)
        auth_service.notification_client.send_password_reset_notification = AsyncMock(
            return_value={"success": True}
        )
        auth_service.event_publisher.publish_password_reset_request = AsyncMock()

        reset_request = PasswordResetRequest(email="test@example.com")

        # Act
        result = await auth_service.forgot_password(reset_request)

        # Assert
        assert "reset_token" in result
        assert result["expires_in_minutes"] == "15"
        auth_service.user_repository.query_email.assert_called_once_with(
            "test@example.com"
        )
        auth_service.notification_client.send_password_reset_notification.assert_called_once()
        auth_service.event_publisher.publish_password_reset_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_forgot_password_user_not_found(self, auth_service):
        """Test forgot password when user not found."""
        # Arrange
        auth_service.user_repository.query_email = AsyncMock(return_value=None)

        reset_request = PasswordResetRequest(email="nonexistent@example.com")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.forgot_password(reset_request)

        assert exc_info.value.status_code == 404
        assert "User with this email does not exist" in exc_info.value.detail

    # Tests for verify_reset_password_token method
    @pytest.mark.asyncio
    async def test_verify_reset_password_token_success(self, auth_service, sample_user):
        """Test successful password reset token verification."""
        # Arrange
        auth_service.user_repository.query_email = AsyncMock(return_value=sample_user)

        with patch("user_service.app.services.auth_service.jwt_handler") as mock_jwt:
            mock_payload = Mock()
            mock_payload.email = "test@example.com"
            mock_jwt.decode_token.return_value = mock_payload

            # Act
            result = await auth_service.verify_reset_password_token("valid_token")

            # Assert
            assert result is True
            auth_service.user_repository.query_email.assert_called_once_with(
                "test@example.com"
            )

    @pytest.mark.asyncio
    async def test_verify_reset_password_token_invalid_token(self, auth_service):
        """Test password reset token verification with invalid token."""
        # Arrange
        with patch("user_service.app.services.auth_service.jwt_handler") as mock_jwt:
            mock_payload = Mock()
            mock_payload.email = None
            mock_jwt.decode_token.return_value = mock_payload

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.verify_reset_password_token("invalid_token")

            assert exc_info.value.status_code == 400
            assert "Invalid token" in exc_info.value.detail

    # Tests for reset_password method
    @pytest.mark.asyncio
    async def test_reset_password_success(self, auth_service, sample_user):
        """Test successful password reset."""
        # Arrange
        auth_service.user_repository.query_email = AsyncMock(return_value=sample_user)
        auth_service.user_repository.update = AsyncMock(return_value=sample_user)
        auth_service.event_publisher.publish_password_reset_confirm = AsyncMock()

        reset_confirm = PasswordResetConfirm(
            email="test@example.com", new_password="NewStrongPass123!"
        )

        # Act
        result = await auth_service.reset_password(reset_confirm)

        # Assert
        assert result == sample_user
        auth_service.user_repository.query_email.assert_called_once_with(
            "test@example.com"
        )
        auth_service.user_repository.update.assert_called_once()
        auth_service.event_publisher.publish_password_reset_confirm.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_password_user_not_found(self, auth_service):
        """Test password reset when user not found."""
        # Arrange
        auth_service.user_repository.query_email = AsyncMock(return_value=None)

        reset_confirm = PasswordResetConfirm(
            email="nonexistent@example.com", new_password="NewStrongPass123!"
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.reset_password(reset_confirm)

        assert exc_info.value.status_code == 404
        assert "User with this email does not exist" in exc_info.value.detail

    # Tests for change_password method
    @pytest.mark.asyncio
    async def test_change_password_success(self, auth_service, sample_user):
        """Test successful password change."""
        # Arrange
        auth_service.user_repository.query_email = AsyncMock(return_value=sample_user)
        auth_service.user_repository.update = AsyncMock(return_value=sample_user)

        change_request = PasswordChangeRequest(
            current_password="OldPass123!", new_password="NewStrongPass123!"
        )

        with patch(
            "user_service.app.services.auth_service.SecurityUtils.verify_password",
            return_value=True,
        ):
            # Act
            result = await auth_service.change_password(change_request, sample_user)

            # Assert
            assert result == sample_user
            auth_service.user_repository.query_email.assert_called_once_with(
                "test@example.com"
            )
            auth_service.user_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_wrong_current_password(
        self, auth_service, sample_user
    ):
        """Test password change with wrong current password."""
        # Arrange
        auth_service.user_repository.query_email = AsyncMock(return_value=sample_user)

        change_request = PasswordChangeRequest(
            current_password="WrongPass123!", new_password="NewStrongPass123!"
        )

        with patch(
            "user_service.app.services.auth_service.SecurityUtils.verify_password",
            return_value=False,
        ):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.change_password(change_request, sample_user)

            assert exc_info.value.status_code == 401
            assert "Current password is incorrect" in exc_info.value.detail

    # Tests for logout_user method
    @pytest.mark.asyncio
    async def test_logout_user_success(self, auth_service, sample_user):
        """Test successful user logout."""
        # Arrange
        auth_service.event_publisher.publish_logout = AsyncMock()

        mock_response = Mock(spec=Response)
        mock_response.delete_cookie = Mock()

        # Act
        result = await auth_service.logout_user(sample_user, mock_response)

        # Assert
        assert result == {"Message": "Logged out successfully."}
        mock_response.delete_cookie.assert_called_once_with(key="access_token")
        auth_service.event_publisher.publish_logout.assert_called_once_with(sample_user)

    @pytest.mark.asyncio
    async def test_logout_user_not_authenticated(self, auth_service):
        """Test logout when user is not authenticated."""
        # Arrange
        mock_response = Mock(spec=Response)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.logout_user(None, mock_response)

        assert exc_info.value.status_code == 401
        assert "User is not authenticated" in exc_info.value.detail

    # Tests for refresh_access_token method
    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, auth_service, sample_user):
        """Test successful access token refresh."""
        # Arrange
        auth_service.user_repository.query_email = AsyncMock(return_value=sample_user)

        with (
            patch("user_service.app.services.auth_service.jwt_handler") as mock_jwt,
            patch("user_service.app.services.auth_service.settings") as mock_settings,
        ):
            mock_payload = Mock()
            mock_payload.user_id = "1"
            mock_payload.email = "test@example.com"
            mock_jwt.decode_token.return_value = mock_payload
            mock_jwt.encode_token.return_value = "new_access_token"
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30

            # Act
            result = await auth_service.refresh_access_token("valid_refresh_token")

            # Assert
            assert result["access_token"] == "new_access_token"
            assert result["token_type"] == "bearer"
            assert result["expires_in"] == 1800  # 30 minutes in seconds
            auth_service.user_repository.query_email.assert_called_once_with(
                "test@example.com"
            )

    @pytest.mark.asyncio
    async def test_refresh_access_token_invalid_token(self, auth_service):
        """Test access token refresh with invalid token."""
        # Arrange
        with patch("user_service.app.services.auth_service.jwt_handler") as mock_jwt:
            mock_payload = Mock()
            mock_payload.user_id = None
            mock_jwt.decode_token.return_value = mock_payload

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.refresh_access_token("invalid_token")

            assert exc_info.value.status_code == 401
            assert "Invalid refresh token" in exc_info.value.detail

    # Tests for validate_password_strength method
    @pytest.mark.asyncio
    async def test_validate_password_strength_strong(self, auth_service):
        """Test password strength validation with strong password."""
        # Act
        result = await auth_service.validate_password_strength("StrongPass123!")

        # Assert
        assert result["is_valid"] is True
        assert result["score"] == 100
        assert "Strong password!" in result["feedback"]
        assert all(result["requirements_met"].values())

    @pytest.mark.asyncio
    async def test_validate_password_strength_weak(self, auth_service):
        """Test password strength validation with weak password."""
        # Act
        result = await auth_service.validate_password_strength("weak")

        # Assert
        assert result["is_valid"] is False
        assert result["score"] == 20  # Only has lowercase letters
        assert len(result["feedback"]) >= 4  # Should have multiple feedback messages
        assert result["requirements_met"]["has_lowercase"] is True
        assert not result["requirements_met"]["min_length"]
        assert not result["requirements_met"]["has_uppercase"]
        assert not result["requirements_met"]["has_digit"]
        assert not result["requirements_met"]["has_special"]

    # Tests for revoke_all_sessions method
    @pytest.mark.asyncio
    async def test_revoke_all_sessions_success(self, auth_service, sample_user):
        """Test successful session revocation."""
        # Arrange
        mock_response = Mock(spec=Response)
        mock_response.delete_cookie = Mock()

        # Act
        result = await auth_service.revoke_all_sessions(sample_user, mock_response)

        # Assert
        assert result == {"message": "All sessions have been revoked successfully."}
        mock_response.delete_cookie.assert_called_once_with(key="access_token")

    @pytest.mark.asyncio
    async def test_revoke_all_sessions_not_authenticated(self, auth_service):
        """Test session revocation when user is not authenticated."""
        # Arrange
        mock_response = Mock(spec=Response)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.revoke_all_sessions(None, mock_response)

        assert exc_info.value.status_code == 401
        assert "User is not authenticated" in exc_info.value.detail
