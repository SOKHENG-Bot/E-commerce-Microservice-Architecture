"""
Unit tests for NotificationClient
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import TimeoutException

from user_service.app.services.notification_client_service import NotificationClient


class TestNotificationClient:
    """Comprehensive unit tests for NotificationClient methods."""

    @pytest.fixture
    def notification_client(self):
        """NotificationClient instance."""
        return NotificationClient()

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return {
            "user_id": 1,
            "email": "test@example.com",
            "username": "testuser",
            "verification_token": "abc123",
            "reset_token": "reset456",
        }

    # Tests for send_welcome_email method
    @pytest.mark.asyncio
    async def test_send_welcome_email_success(
        self, notification_client, sample_user_data
    ):
        """Test successful welcome email sending."""
        # Setup
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"notification_id": "notif_123"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Execute
            result = await notification_client.send_welcome_email(
                user_id=sample_user_data["user_id"],
                email=sample_user_data["email"],
                username=sample_user_data["username"],
                verification_token=sample_user_data["verification_token"],
            )

            # Assert
            assert result == {"success": True, "notification_id": "notif_123"}
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert (
                call_args[0][0]
                == "http://notification_service:8000/api/v1/notifications/send"
            )
            assert call_args[1]["params"] == {"user_id": 1}
            notification_data = call_args[1]["json"]
            assert notification_data["type"] == "email"
            assert notification_data["recipient"] == sample_user_data["email"]
            assert "Welcome to E-Commerce Platform" in notification_data["subject"]
            assert (
                sample_user_data["username"]
                in notification_data["template_data"]["username"]
            )

    @pytest.mark.asyncio
    async def test_send_welcome_email_success_no_username(
        self, notification_client, sample_user_data
    ):
        """Test welcome email sending without username."""
        # Setup
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"notification_id": "notif_123"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Execute
            result = await notification_client.send_welcome_email(
                user_id=sample_user_data["user_id"],
                email=sample_user_data["email"],
                verification_token=sample_user_data["verification_token"],
            )

            # Assert
            assert result == {"success": True, "notification_id": "notif_123"}
            call_args = mock_client.post.call_args
            notification_data = call_args[1]["json"]
            assert (
                notification_data["template_data"]["username"] == "test"
            )  # email prefix

    @pytest.mark.asyncio
    async def test_send_welcome_email_success_no_verification_token(
        self, notification_client, sample_user_data
    ):
        """Test welcome email sending without verification token."""
        # Setup
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"notification_id": "notif_123"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Execute
            result = await notification_client.send_welcome_email(
                user_id=sample_user_data["user_id"],
                email=sample_user_data["email"],
                username=sample_user_data["username"],
            )

            # Assert
            assert result == {"success": True, "notification_id": "notif_123"}
            call_args = mock_client.post.call_args
            notification_data = call_args[1]["json"]
            assert (
                "Your account is ready to use!"
                in notification_data["template_data"]["verification_message"]
            )

    @pytest.mark.asyncio
    async def test_send_welcome_email_http_error(
        self, notification_client, sample_user_data
    ):
        """Test welcome email sending with HTTP error response."""
        # Setup
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.content = b'{"error": "Bad request"}'
        mock_response.json.return_value = {"error": "Bad request"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Execute
            result = await notification_client.send_welcome_email(
                user_id=sample_user_data["user_id"],
                email=sample_user_data["email"],
                username=sample_user_data["username"],
            )

            # Assert
            assert result == {"success": False, "error": "HTTP 400"}

    @pytest.mark.asyncio
    async def test_send_welcome_email_timeout(
        self, notification_client, sample_user_data
    ):
        """Test welcome email sending with timeout exception."""
        # Setup
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.side_effect = TimeoutException("Request timeout")
            mock_client_class.return_value = mock_client

            # Execute
            result = await notification_client.send_welcome_email(
                user_id=sample_user_data["user_id"],
                email=sample_user_data["email"],
                username=sample_user_data["username"],
            )

            # Assert
            assert result == {"success": False, "error": "Request timeout"}

    @pytest.mark.asyncio
    async def test_send_welcome_email_exception(
        self, notification_client, sample_user_data
    ):
        """Test welcome email sending with general exception."""
        # Setup
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.side_effect = Exception("Network error")
            mock_client_class.return_value = mock_client

            # Execute
            result = await notification_client.send_welcome_email(
                user_id=sample_user_data["user_id"],
                email=sample_user_data["email"],
                username=sample_user_data["username"],
            )

            # Assert
            assert result == {"success": False, "error": "Network error"}

    # Tests for send_email_verification method
    @pytest.mark.asyncio
    async def test_send_email_verification_success(
        self, notification_client, sample_user_data
    ):
        """Test successful email verification sending."""
        # Setup
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"notification_id": "verif_123"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Execute
            result = await notification_client.send_email_verification(
                user_id=sample_user_data["user_id"],
                email=sample_user_data["email"],
                verification_token=sample_user_data["verification_token"],
                username=sample_user_data["username"],
            )

            # Assert
            assert result == {"success": True, "notification_id": "verif_123"}
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            notification_data = call_args[1]["json"]
            assert notification_data["priority"] == "high"
            assert "Verify Your Email Address" in notification_data["subject"]
            assert (
                sample_user_data["verification_token"]
                in notification_data["template_data"]["verification_token"]
            )

    @pytest.mark.asyncio
    async def test_send_email_verification_http_error(
        self, notification_client, sample_user_data
    ):
        """Test email verification sending with HTTP error."""
        # Setup
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.content = b'{"error": "Internal server error"}'
        mock_response.json.return_value = {"error": "Internal server error"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Execute
            result = await notification_client.send_email_verification(
                user_id=sample_user_data["user_id"],
                email=sample_user_data["email"],
                verification_token=sample_user_data["verification_token"],
            )

            # Assert
            assert result == {"success": False, "error": "HTTP 500"}

    @pytest.mark.asyncio
    async def test_send_email_verification_exception(
        self, notification_client, sample_user_data
    ):
        """Test email verification sending with exception."""
        # Setup
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.side_effect = Exception("Connection failed")
            mock_client_class.return_value = mock_client

            # Execute
            result = await notification_client.send_email_verification(
                user_id=sample_user_data["user_id"],
                email=sample_user_data["email"],
                verification_token=sample_user_data["verification_token"],
            )

            # Assert
            assert result == {"success": False, "error": "Connection failed"}

    # Tests for send_password_reset_notification method
    @pytest.mark.asyncio
    async def test_send_password_reset_success(
        self, notification_client, sample_user_data
    ):
        """Test successful password reset notification sending."""
        # Setup
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"notification_id": "reset_123"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Execute
            result = await notification_client.send_password_reset_notification(
                user_id=sample_user_data["user_id"],
                email=sample_user_data["email"],
                reset_token=sample_user_data["reset_token"],
                username=sample_user_data["username"],
            )

            # Assert
            assert result == {"success": True, "notification_id": "reset_123"}
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            notification_data = call_args[1]["json"]
            assert notification_data["priority"] == "high"
            assert "Password Reset Request" in notification_data["subject"]
            assert (
                sample_user_data["reset_token"]
                in notification_data["template_data"]["reset_token"]
            )

    @pytest.mark.asyncio
    async def test_send_password_reset_http_error(
        self, notification_client, sample_user_data
    ):
        """Test password reset notification with HTTP error."""
        # Setup
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.content = b""  # Empty content

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Execute
            result = await notification_client.send_password_reset_notification(
                user_id=sample_user_data["user_id"],
                email=sample_user_data["email"],
                reset_token=sample_user_data["reset_token"],
            )

            # Assert
            assert result == {"success": False, "error": "HTTP 422"}

    @pytest.mark.asyncio
    async def test_send_password_reset_exception(
        self, notification_client, sample_user_data
    ):
        """Test password reset notification with exception."""
        # Setup
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.side_effect = Exception("Service unavailable")
            mock_client_class.return_value = mock_client

            # Execute
            result = await notification_client.send_password_reset_notification(
                user_id=sample_user_data["user_id"],
                email=sample_user_data["email"],
                reset_token=sample_user_data["reset_token"],
            )

            # Assert
            assert result == {"success": False, "error": "Service unavailable"}

    # Tests for test_connection method
    @pytest.mark.asyncio
    async def test_test_connection_success(self, notification_client):
        """Test successful connection to notification service."""
        # Setup
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Execute
            result = await notification_client.test_connection()

            # Assert
            assert result == {
                "success": True,
                "message": "Notification service is healthy",
            }
            mock_client.get.assert_called_once_with(
                "http://notification_service:8000/health"
            )

    @pytest.mark.asyncio
    async def test_test_connection_http_error(self, notification_client):
        """Test connection test with HTTP error."""
        # Setup
        mock_response = Mock()
        mock_response.status_code = 503

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Execute
            result = await notification_client.test_connection()

            # Assert
            assert result == {"success": False, "error": "HTTP 503"}

    @pytest.mark.asyncio
    async def test_test_connection_exception(self, notification_client):
        """Test connection test with exception."""
        # Setup
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.side_effect = Exception("Connection refused")
            mock_client_class.return_value = mock_client

            # Execute
            result = await notification_client.test_connection()

            # Assert
            assert result == {"success": False, "error": "Connection refused"}
