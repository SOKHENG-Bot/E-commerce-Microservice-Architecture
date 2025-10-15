import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx
from jinja2 import DictLoader, Environment

from ..core.settings import get_settings
from ..middleware.logging import create_enhanced_logger

logger = logging.getLogger(__name__)
settings = get_settings()


class SMSProvider:
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_FROM_NUMBER
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"

        # Initialize Jinja2 for templating
        self.template_env = Environment(loader=DictLoader({}))

        # Initialize enhanced logger for detailed provider logging
        self.logger = create_enhanced_logger("notification_service_sms_provider")

    async def send_sms(
        self,
        to_number: str,
        content: str,
        template_data: Optional[Dict[str, Any]] = None,
        is_html: bool = False,
    ) -> Dict[str, Any]:
        """
        Send an SMS using Twilio

        Args:
            to_number: Recipient phone number (E.164 format)
            content: SMS content (can be template)
            template_data: Data for template rendering
            is_html: Whether content is HTML (ignored for SMS)

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

            # Validate phone number format
            if not self.validate_phone_number(to_number):
                return {
                    "success": False,
                    "error": f"Invalid phone number format: {to_number}",
                    "provider": "twilio",
                    "recipient": to_number,
                }

            # Prepare request data
            data: Dict[str, str] = {
                "From": self.from_number or "",
                "To": to_number,
                "Body": rendered_content[:1600],  # Twilio SMS limit
            }

            # Prepare auth - only if credentials are available
            auth = None
            if self.account_sid and self.auth_token:
                auth = (self.account_sid, self.auth_token)

            # Send SMS via Twilio API
            async with httpx.AsyncClient() as client:
                if auth is not None:
                    response = await client.post(
                        f"{self.base_url}/Messages.json",
                        auth=auth,
                        data=data,
                        timeout=30.0,
                    )
                else:
                    response = await client.post(
                        f"{self.base_url}/Messages.json",
                        data=data,
                        timeout=30.0,
                    )

                if response.status_code == 201:
                    result = response.json()
                    return {
                        "success": True,
                        "message_id": result.get("sid"),
                        "provider": "twilio",
                        "recipient": to_number,
                        "status": result.get("status"),
                        "price": result.get("price"),
                        "currency": result.get("price_unit"),
                    }
                else:
                    error_data: Dict[str, Any] = (
                        response.json() if response.content else {}
                    )
                    return {
                        "success": False,
                        "error": error_data.get(
                            "message", f"HTTP {response.status_code}"
                        ),
                        "error_code": error_data.get("code"),
                        "provider": "twilio",
                        "recipient": to_number,
                    }

        except httpx.TimeoutException:
            self.logger.error(
                "Timeout sending SMS",
                extra={
                    "correlation_id": getattr(
                        asyncio.current_task(), "correlation_id", None
                    ),
                    "recipient": to_number,
                    "provider": "twilio",
                    "error_type": "TimeoutException",
                    "error_message": "Request timeout",
                    "event_type": "sms_send_timeout",
                },
            )
            return {
                "success": False,
                "error": "Request timeout",
                "provider": "twilio",
                "recipient": to_number,
            }
        except Exception as e:
            self.logger.error(
                "Failed to send SMS",
                extra={
                    "correlation_id": getattr(
                        asyncio.current_task(), "correlation_id", None
                    ),
                    "recipient": to_number,
                    "provider": "twilio",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "event_type": "sms_send_failed",
                },
            )
            return {
                "success": False,
                "error": str(e),
                "provider": "twilio",
                "recipient": to_number,
            }

    async def send_bulk_sms(
        self,
        recipients: List[str],
        content: str,
        template_data: Optional[Dict[str, Any]] = None,
        batch_size: int = 5,
        delay_between_batches: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Send bulk SMS with rate limiting

        Args:
            recipients: List of phone numbers
            content: SMS content
            template_data: Template data
            batch_size: Number of SMS per batch
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
            tasks = [self.send_sms(phone, content, template_data) for phone in batch]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for phone, result in zip(batch, results):
                if isinstance(result, Exception):
                    total_failed += 1
                    failed_recipients.append(phone)
                    self.logger.error(
                        "Failed to send SMS in bulk operation",
                        extra={
                            "correlation_id": getattr(
                                asyncio.current_task(), "correlation_id", None
                            ),
                            "recipient": phone,
                            "provider": "twilio",
                            "error_type": type(result).__name__,
                            "error_message": str(result),
                            "event_type": "bulk_sms_send_failed",
                        },
                    )
                elif isinstance(result, dict) and result.get("success"):
                    total_sent += 1
                else:
                    total_failed += 1
                    failed_recipients.append(phone)

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

    def validate_phone_number(self, phone: str) -> bool:
        """
        Validate phone number format (basic E.164 validation)

        Args:
            phone: Phone number to validate

        Returns:
            True if valid, False otherwise
        """
        import re

        # Remove whitespace and common separators
        cleaned = re.sub(r"[\s\-\(\)\.]", "", phone)

        # Check E.164 format: + followed by 1-15 digits
        pattern = r"^\+[1-9]\d{1,14}$"
        return bool(re.match(pattern, cleaned))

    async def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """
        Get the status of a sent message

        Args:
            message_sid: Twilio message SID

        Returns:
            Dict with message status information
        """
        try:
            # Prepare auth - only if credentials are available
            auth = None
            if self.account_sid and self.auth_token:
                auth = (self.account_sid, self.auth_token)

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/Messages/{message_sid}.json",
                    auth=auth,
                    timeout=15.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "status": data.get("status"),
                        "error_code": data.get("error_code"),
                        "error_message": data.get("error_message"),
                        "price": data.get("price"),
                        "date_sent": data.get("date_sent"),
                        "date_updated": data.get("date_updated"),
                    }
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            self.logger.error(
                "Failed to get message status",
                extra={
                    "correlation_id": getattr(
                        asyncio.current_task(), "correlation_id", None
                    ),
                    "message_sid": message_sid,
                    "provider": "twilio",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "event_type": "sms_status_check_failed",
                },
            )
            return {"success": False, "error": str(e)}

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test Twilio API connection

        Returns:
            Dict with connection test result
        """
        try:
            # Prepare auth - only if credentials are available
            auth = None
            if self.account_sid and self.auth_token:
                auth = (self.account_sid, self.auth_token)

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}.json",
                    auth=auth,
                    timeout=15.0,
                )

                if response.status_code == 200:
                    return {"success": True, "message": "Twilio connection successful"}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            self.logger.error(
                "Twilio connection test failed",
                extra={
                    "correlation_id": getattr(
                        asyncio.current_task(), "correlation_id", None
                    ),
                    "provider": "twilio",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "event_type": "twilio_connection_test_failed",
                },
            )
            return {"success": False, "error": str(e)}
