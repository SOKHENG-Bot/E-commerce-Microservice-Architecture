import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import aiosmtplib
from jinja2 import DictLoader, Environment

from ..core.settings import get_settings
from ..middleware.logging_middleware import create_enhanced_logger

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailProvider:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = int(settings.SMTP_PORT) if settings.SMTP_PORT else 587
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_use_tls = settings.SMTP_USE_TLS
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME

        # Initialize Jinja2 for templating
        self.template_env = Environment(loader=DictLoader({}))

        # Initialize enhanced logger for detailed provider logging
        self.logger = create_enhanced_logger("notification_service_email_provider")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        template_data: Optional[Dict[str, Any]] = None,
        is_html: bool = False,
    ) -> Dict[str, Any]:
        """
        Send an email using SMTP

        Args:
            to_email: Recipient email address
            subject: Email subject
            content: Email content (can be template)
            template_data: Data for template rendering
            is_html: Whether content is HTML

        Returns:
            Dict containing delivery result
        """
        try:
            # Render template if template_data provided
            if template_data:
                template = self.template_env.from_string(content)
                rendered_content = template.render(**template_data)
            else:
                rendered_content = content

            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            # Add content
            if is_html:
                part = MIMEText(rendered_content, "html")
            else:
                part = MIMEText(rendered_content, "plain")

            message.attach(part)

            # Send email
            await self._send_smtp_email(message, to_email)

            return {
                "success": True,
                "message_id": None,  # SMTP doesn't always return message ID
                "provider": "smtp",
                "recipient": to_email,
            }

        except Exception as e:
            self.logger.error(
                "Failed to send email",
                extra={
                    "correlation_id": getattr(
                        asyncio.current_task(), "correlation_id", None
                    ),
                    "recipient": to_email,
                    "provider": "smtp",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "event_type": "email_send_failed",
                },
            )
            return {
                "success": False,
                "error": str(e),
                "provider": "smtp",
                "recipient": to_email,
            }

    async def _send_smtp_email(self, message: MIMEMultipart, to_email: str):
        """Send email via SMTP"""
        try:
            if self.smtp_use_tls:
                # Use TLS (implicit SSL)
                if self.smtp_username and self.smtp_password:
                    await aiosmtplib.send(
                        message,
                        hostname=self.smtp_host,
                        port=self.smtp_port,
                        username=self.smtp_username,
                        password=self.smtp_password,
                        use_tls=True,
                    )
                else:
                    await aiosmtplib.send(
                        message,
                        hostname=self.smtp_host,
                        port=self.smtp_port,
                        use_tls=True,
                    )
            else:
                # No TLS/SSL - plain SMTP (for MailHog and local testing)
                if self.smtp_username and self.smtp_password:
                    await aiosmtplib.send(
                        message,
                        hostname=self.smtp_host,
                        port=self.smtp_port,
                        username=self.smtp_username,
                        password=self.smtp_password,
                        use_tls=False,
                        start_tls=False,
                    )
                else:
                    await aiosmtplib.send(
                        message,
                        hostname=self.smtp_host,
                        port=self.smtp_port,
                        use_tls=False,
                        start_tls=False,
                    )

        except aiosmtplib.SMTPException as e:
            self.logger.error(
                "SMTP error sending email",
                extra={
                    "correlation_id": getattr(
                        asyncio.current_task(), "correlation_id", None
                    ),
                    "recipient": to_email,
                    "provider": "smtp",
                    "error_type": "SMTPException",
                    "error_message": str(e),
                    "event_type": "smtp_error",
                },
            )
            raise
        except Exception as e:
            self.logger.error(
                "Unexpected error sending email",
                extra={
                    "correlation_id": getattr(
                        asyncio.current_task(), "correlation_id", None
                    ),
                    "recipient": to_email,
                    "provider": "smtp",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "event_type": "email_send_unexpected_error",
                },
            )
            raise

    async def send_bulk_email(
        self,
        recipients: list[str],
        subject: str,
        content: str,
        template_data: Optional[Dict[str, Any]] = None,
        is_html: bool = False,
        batch_size: int = 10,
        delay_between_batches: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Send bulk emails with rate limiting

        Args:
            recipients: List of email addresses
            subject: Email subject
            content: Email content
            template_data: Template data
            is_html: Whether content is HTML
            batch_size: Number of emails per batch
            delay_between_batches: Delay between batches in seconds

        Returns:
            Dict with success/failure counts
        """
        total_sent = 0
        total_failed = 0
        failed_recipients: List[str] = []

        # Process in batches
        for i in range(0, len(recipients), batch_size):
            batch = recipients[i : i + batch_size]

            # Send batch concurrently
            tasks = [
                self.send_email(email, subject, content, template_data, is_html)
                for email in batch
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for email, result in zip(batch, results):
                if isinstance(result, Exception):
                    total_failed += 1
                    failed_recipients.append(email)
                    self.logger.error(
                        "Failed to send email in bulk operation",
                        extra={
                            "correlation_id": getattr(
                                asyncio.current_task(), "correlation_id", None
                            ),
                            "recipient": email,
                            "provider": "smtp",
                            "error_type": type(result).__name__,
                            "error_message": str(result),
                            "event_type": "bulk_email_send_failed",
                        },
                    )
                elif isinstance(result, dict) and result.get("success"):
                    total_sent += 1
                else:
                    total_failed += 1
                    failed_recipients.append(email)

            # Delay between batches (except for last batch)
            if i + batch_size < len(recipients):
                await asyncio.sleep(delay_between_batches)

        return {
            "total_recipients": len(recipients),
            "total_sent": total_sent,
            "total_failed": total_failed,
            "failed_recipients": failed_recipients,
            "success_rate": (total_sent / len(recipients)) * 100 if recipients else 0,
        }

    async def validate_email_address(self, email: str) -> bool:
        """
        Validate email address format

        Args:
            email: Email address to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            from email_validator import validate_email

            validate_email(email)
            return True
        except Exception:
            # Fallback to basic validation if email-validator not installed or validation fails
            import re

            pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            return bool(re.match(pattern, email))

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test SMTP connection

        Returns:
            Dict with connection test result
        """
        try:
            if self.smtp_use_tls:
                server = aiosmtplib.SMTP(
                    hostname=self.smtp_host, port=self.smtp_port, use_tls=True
                )
            else:
                server = aiosmtplib.SMTP(hostname=self.smtp_host, port=self.smtp_port)

            await server.connect()

            if self.smtp_username and self.smtp_password:
                await server.login(self.smtp_username, self.smtp_password)

            await server.quit()

            return {"success": True, "message": "SMTP connection successful"}

        except Exception as e:
            self.logger.error(
                "SMTP connection test failed",
                extra={
                    "correlation_id": getattr(
                        asyncio.current_task(), "correlation_id", None
                    ),
                    "provider": "smtp",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "event_type": "smtp_connection_test_failed",
                },
            )
            return {"success": False, "error": str(e)}
