import asyncio
import logging
from typing import Any, Dict, List, Optional

from jinja2 import DictLoader, Environment
from sendgrid import SendGridAPIClient  # type: ignore
from sendgrid.helpers.mail import Content, Email, Mail, To  # type: ignore

from ..core.settings import get_settings

settings = get_settings()


class EmailProvider:
    def __init__(self):
        self.from_email: str = settings.FROM_EMAIL or ""
        self.from_name: str = settings.FROM_NAME or ""

        # SendGrid configuration
        self.sendgrid_api_key: str = settings.SENDGRID_API_KEY or ""

        # Validate required settings
        if not self.from_email:
            raise ValueError("FROM_EMAIL setting is required")
        if not self.sendgrid_api_key:
            raise ValueError("SENDGRID_API_KEY setting is required")

        # Initialize Jinja2 for templating
        self.template_env: Environment = Environment(loader=DictLoader({}))

        # Initialize enhanced logger for detailed provider logging
        self.logger: logging.Logger = logging.getLogger(
            "notification_service_email_provider"
        )

    async def send_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        template_data: Optional[Dict[str, Any]] = None,
        is_html: bool = False,
    ) -> Dict[str, Any]:
        """
        Send an email using SendGrid

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

            # Send email via SendGrid
            return await self._send_sendgrid_email(
                to_email, subject, rendered_content, is_html
            )

        except Exception as e:
            correlation_id = None
            try:
                task = asyncio.current_task()
                correlation_id = getattr(task, "correlation_id", None)
            except (AttributeError, RuntimeError):
                pass

            self.logger.error(
                "Failed to send email",
                extra={
                    "correlation_id": correlation_id,
                    "recipient": to_email,
                    "provider": "sendgrid",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "event_type": "email_send_failed",
                },
            )
            return {
                "success": False,
                "error": str(e),
                "provider": "sendgrid",
                "recipient": to_email,
            }

    async def _send_sendgrid_email(
        self, to_email: str, subject: str, content: str, is_html: bool = False
    ) -> Dict[str, Any]:
        """Send email via SendGrid"""
        try:
            sg = SendGridAPIClient(api_key=self.sendgrid_api_key)  # type: ignore

            from_email_obj = Email(self.from_email, self.from_name)  # type: ignore
            to_email_obj = To(to_email)  # type: ignore

            mail_obj = Mail(from_email_obj, to_email_obj, subject)  # type: ignore

            if is_html:
                # Send both HTML and plain text versions for better compatibility
                # Extract plain text from HTML by removing tags (simple approach)
                import re

                plain_text = re.sub(r"<[^>]+>", "", content)  # Remove HTML tags
                plain_text = re.sub(
                    r"\s+", " ", plain_text
                ).strip()  # Clean up whitespace

                # Add plain text content
                plain_content_obj = Content("text/plain", plain_text)  # type: ignore
                mail_obj.add_content(plain_content_obj)  # type: ignore

                # Add HTML content
                html_content_obj = Content("text/html", content)  # type: ignore
                mail_obj.add_content(html_content_obj)  # type: ignore
            else:
                # Plain text only
                content_obj = Content("text/plain", content)  # type: ignore
                mail_obj.add_content(content_obj)  # type: ignore

            response = sg.send(mail_obj)  # type: ignore

            return {
                "success": True,
                "message_id": response.headers.get("X-Message-Id"),  # type: ignore
                "provider": "sendgrid",
                "recipient": to_email,
                "status_code": response.status_code,  # type: ignore
            }

        except Exception as e:
            correlation_id = None
            try:
                task = asyncio.current_task()
                correlation_id = getattr(task, "correlation_id", None)
            except (AttributeError, RuntimeError):
                pass

            self.logger.error(
                "SendGrid error sending email",
                extra={
                    "correlation_id": correlation_id,
                    "recipient": to_email,
                    "provider": "sendgrid",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "event_type": "sendgrid_error",
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
                    correlation_id = None
                    try:
                        task = asyncio.current_task()
                        correlation_id = getattr(task, "correlation_id", None)
                    except (AttributeError, RuntimeError):
                        pass

                    self.logger.error(
                        "Failed to send email in bulk operation",
                        extra={
                            "correlation_id": correlation_id,
                            "recipient": email,
                            "provider": "sendgrid",
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
        Test SendGrid connection

        Returns:
            Dict with connection test result
        """
        return await self._test_sendgrid_connection()

    async def _test_sendgrid_connection(self) -> Dict[str, Any]:
        """
        Test SendGrid connection

        Returns:
            Dict with connection test result
        """
        try:
            sg = SendGridAPIClient(api_key=self.sendgrid_api_key)  # type: ignore

            # Test API key by making a simple request
            response = sg.client.api_keys.get()  # type: ignore

            if response.status_code == 200:  # type: ignore
                return {"success": True, "message": "SendGrid connection successful"}
            else:
                return {
                    "success": False,
                    "error": f"SendGrid API returned status {response.status_code}",  # type: ignore
                }

        except Exception as e:
            correlation_id = None
            try:
                task = asyncio.current_task()
                correlation_id = getattr(task, "correlation_id", None)
            except (AttributeError, RuntimeError):
                pass

            self.logger.error(
                "SendGrid connection test failed",
                extra={
                    "correlation_id": correlation_id,
                    "provider": "sendgrid",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "event_type": "sendgrid_connection_test_failed",
                },
            )
            return {"success": False, "error": str(e)}
