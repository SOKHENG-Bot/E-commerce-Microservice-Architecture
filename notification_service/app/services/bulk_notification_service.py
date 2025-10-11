"""
Bulk notification service for mass notification sending with segmentation and batch processing.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.notification import NotificationStatus
from ..services.notification_service import NotificationService
from ..utils.logging import setup_notification_logging

logger = setup_notification_logging("bulk_notification_service", log_level="INFO")


class BulkNotificationService:
    """
    Service for handling bulk notifications with segmentation and batch processing.
    """

    def __init__(
        self, session: AsyncSession, notification_service: NotificationService
    ):
        self.session = session
        self.notification_service = notification_service
        self.batch_size = 50  # Process 50 notifications at a time
        self.max_concurrent_batches = 5  # Maximum concurrent batch processing

    async def send_bulk_notification(
        self,
        user_ids: List[int],
        notification_type: str,
        channel: str,
        subject: Optional[str],
        content: str,
        template_id: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None,
        priority: str = "medium",
        batch_size: Optional[int] = None,
        max_concurrent: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Send bulk notifications to multiple users with batch processing.

        Args:
            user_ids: List of user IDs to send notifications to
            notification_type: Type of notification
            channel: Notification channel (email, sms, push)
            subject: Notification subject
            content: Notification content
            template_id: Template ID to use
            template_data: Template data
            priority: Notification priority
            batch_size: Size of each processing batch
            max_concurrent: Maximum concurrent batches

        Returns:
            Bulk notification result with job tracking
        """
        try:
            # Generate job ID for tracking
            job_id = str(uuid4())

            # Use provided batch settings or defaults
            effective_batch_size = batch_size or self.batch_size
            effective_max_concurrent = max_concurrent or self.max_concurrent_batches

            logger.info(
                "Starting bulk notification job",
                extra={
                    "job_id": job_id,
                    "total_users": len(user_ids),
                    "notification_type": notification_type,
                    "channel": channel,
                    "batch_size": effective_batch_size,
                    "max_concurrent": effective_max_concurrent,
                },
            )

            # Create notification records in batches
            notification_ids = await self._create_bulk_notifications(
                user_ids=user_ids,
                notification_type=notification_type,
                channel=channel,
                subject=subject,
                content=content,
                template_id=template_id,
                template_data=template_data,
                priority=priority,
                job_id=job_id,
            )

            # Process notifications in concurrent batches
            results = await self._process_bulk_notifications(
                notification_ids=notification_ids,
                batch_size=effective_batch_size,
                max_concurrent=effective_max_concurrent,
                job_id=job_id,
            )

            # Calculate final statistics
            total_sent = sum(batch["sent"] for batch in results)
            total_failed = sum(batch["failed"] for batch in results)
            total_processing_time = sum(batch["processing_time"] for batch in results)

            success_rate = (total_sent / len(user_ids)) * 100 if user_ids else 0

            logger.info(
                "Bulk notification job completed",
                extra={
                    "job_id": job_id,
                    "total_users": len(user_ids),
                    "total_sent": total_sent,
                    "total_failed": total_failed,
                    "success_rate": success_rate,
                    "total_processing_time": total_processing_time,
                },
            )

            return {
                "job_id": job_id,
                "total_users": len(user_ids),
                "total_sent": total_sent,
                "total_failed": total_failed,
                "success_rate": success_rate,
                "processing_time_seconds": total_processing_time,
                "batch_results": results,
            }

        except Exception as e:
            logger.error(f"Failed to send bulk notification: {e}")
            raise

    async def _create_bulk_notifications(
        self,
        user_ids: List[int],
        notification_type: str,
        channel: str,
        subject: Optional[str],
        content: str,
        template_id: Optional[str],
        template_data: Optional[Dict[str, Any]],
        priority: str,
        job_id: str,
    ) -> List[int]:
        """Create notification records for bulk sending."""
        try:
            notification_ids = []

            # Create notifications in batches to avoid memory issues
            batch_size = 100
            for i in range(0, len(user_ids), batch_size):
                batch_user_ids = user_ids[i : i + batch_size]

                # Get recipient info for each user (simplified - in real implementation,
                # this would query user service for email/phone/token)
                notifications_data = []
                for user_id in batch_user_ids:
                    # Mock recipient resolution - replace with actual user service call
                    recipient = await self._resolve_recipient(user_id, channel)

                    if recipient:
                        notifications_data.append(
                            {
                                "user_id": user_id,
                                "type": notification_type,
                                "channel": channel,
                                "recipient": recipient,
                                "subject": subject,
                                "content": content,
                                "template_id": template_id,
                                "template_data": template_data,
                                "status": NotificationStatus.PENDING.value,
                                "priority": priority,
                                "created_at": datetime.now(timezone.utc).replace(
                                    tzinfo=None
                                ),
                                "updated_at": datetime.now(timezone.utc).replace(
                                    tzinfo=None
                                ),
                            }
                        )

                # Bulk insert notifications
                if notifications_data:
                    # Use raw SQL for bulk insert performance
                    values_placeholders = ", ".join(
                        f"({', '.join([':' + str(j) + '_' + k for k in data.keys()])})"
                        for j, data in enumerate(notifications_data)
                    )

                    columns = list(notifications_data[0].keys())
                    columns_str = ", ".join(columns)

                    query = f"""
                        INSERT INTO notifications ({columns_str})
                        VALUES {values_placeholders}
                        RETURNING id
                    """

                    # Flatten parameters
                    params = {}
                    for j, data in enumerate(notifications_data):
                        for k, v in data.items():
                            params[f"{j}_{k}"] = v

                    result = await self.session.execute(text(query), params)
                    batch_ids = result.fetchall()
                    notification_ids.extend([row[0] for row in batch_ids])

            logger.info(
                f"Created {len(notification_ids)} notification records for job {job_id}"
            )
            return notification_ids

        except Exception as e:
            logger.error(f"Failed to create bulk notifications: {e}")
            raise

    async def _process_bulk_notifications(
        self,
        notification_ids: List[int],
        batch_size: int,
        max_concurrent: int,
        job_id: str,
    ) -> List[Dict[str, Any]]:
        """Process notifications in concurrent batches."""
        try:
            results = []

            # Split notification IDs into batches
            batches = [
                notification_ids[i : i + batch_size]
                for i in range(0, len(notification_ids), batch_size)
            ]

            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(max_concurrent)

            async def process_batch(
                batch: List[int], batch_index: int
            ) -> Dict[str, Any]:
                async with semaphore:
                    start_time = datetime.now(timezone.utc)
                    sent = 0
                    failed = 0

                    try:
                        # Process each notification in the batch
                        for notification_id in batch:
                            try:
                                await self._send_single_notification(notification_id)
                                sent += 1
                            except Exception as e:
                                logger.error(
                                    f"Failed to send notification {notification_id}: {e}"
                                )
                                failed += 1

                        processing_time = (
                            datetime.now(timezone.utc) - start_time
                        ).total_seconds()

                        batch_result = {
                            "batch_index": batch_index,
                            "batch_size": len(batch),
                            "sent": sent,
                            "failed": failed,
                            "processing_time": processing_time,
                        }

                        logger.info(
                            f"Processed batch {batch_index} for job {job_id}",
                            extra=batch_result,
                        )
                        return batch_result

                    except Exception as e:
                        logger.error(f"Failed to process batch {batch_index}: {e}")
                        processing_time = (
                            datetime.now(timezone.utc) - start_time
                        ).total_seconds()
                        return {
                            "batch_index": batch_index,
                            "batch_size": len(batch),
                            "sent": 0,
                            "failed": len(batch),
                            "processing_time": processing_time,
                            "error": str(e),
                        }

            # Process all batches concurrently
            tasks = [process_batch(batch, i) for i, batch in enumerate(batches)]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle results and exceptions
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch processing exception: {result}")
                    results.append(
                        {
                            "batch_index": -1,
                            "error": str(result),
                            "sent": 0,
                            "failed": 0,
                            "processing_time": 0,
                        }
                    )
                else:
                    results.append(result)

            return results

        except Exception as e:
            logger.error(f"Failed to process bulk notifications: {e}")
            raise

    async def _send_single_notification(self, notification_id: int) -> None:
        """Send a single notification from bulk job."""
        try:
            # Get notification details
            result = await self.session.execute(
                text("SELECT * FROM notifications WHERE id = :id"),
                {"id": notification_id},
            )
            notification = result.fetchone()

            if not notification:
                raise ValueError(f"Notification {notification_id} not found")

            # Send based on channel
            if notification.channel == "email":
                await self.notification_service.send_email_notification(
                    user_id=notification.user_id,
                    notification_type=notification.type,
                    template_data=notification.template_data,
                    correlation_id=str(notification_id),
                )
            elif notification.channel == "sms":
                await self.notification_service.send_sms_notification(
                    user_id=notification.user_id,
                    phone_number=notification.recipient,
                    message=notification.content,
                    correlation_id=str(notification_id),
                )
            elif notification.channel == "push":
                await self.notification_service.send_push_notification(
                    user_id=notification.user_id,
                    device_token=notification.recipient,
                    title=notification.subject or "Notification",
                    message=notification.content,
                    correlation_id=str(notification_id),
                )
            else:
                raise ValueError(f"Unsupported channel: {notification.channel}")

            # Update notification status
            await self.session.execute(
                text("""
                    UPDATE notifications
                    SET status = :status, sent_at = :sent_at, updated_at = :updated_at
                    WHERE id = :id
                """),
                {
                    "id": notification_id,
                    "status": NotificationStatus.SENT.value,
                    "sent_at": datetime.now(timezone.utc).replace(tzinfo=None),
                    "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
                },
            )
            await self.session.commit()

        except Exception as e:
            # Update notification status to failed
            await self.session.execute(
                text("""
                    UPDATE notifications
                    SET status = :status, failure_reason = :reason, updated_at = :updated_at
                    WHERE id = :id
                """),
                {
                    "id": notification_id,
                    "status": NotificationStatus.FAILED.value,
                    "reason": str(e),
                    "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
                },
            )
            await self.session.commit()
            raise

    async def _resolve_recipient(self, user_id: int, channel: str) -> Optional[str]:
        """Resolve recipient information for a user and channel."""
        try:
            # This is a simplified implementation
            # In a real system, this would call the user service to get user contact info

            # Mock implementation - replace with actual user service call
            if channel == "email":
                return f"user{user_id}@example.com"
            elif channel == "sms":
                return f"+123456789{user_id % 10}"
            elif channel == "push":
                return f"device_token_{user_id}"
            else:
                return None

        except Exception as e:
            logger.error(
                f"Failed to resolve recipient for user {user_id}, channel {channel}: {e}"
            )
            return None
