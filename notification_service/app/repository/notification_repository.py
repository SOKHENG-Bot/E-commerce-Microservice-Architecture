from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import and_, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.notification import Notification, NotificationPriority, NotificationStatus
from ..models.template import Template
from ..schemas.notification import NotificationCreate, NotificationUpdate
from ..schemas.notification import NotificationStatus as SchemaNotificationStatus


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_notification(
        self, notification_data: NotificationCreate, user_id: int
    ) -> Notification:
        """Create a new notification"""
        db_notification = Notification(
            user_id=user_id,
            type=notification_data.type.value,
            channel=notification_data.channel,
            recipient=notification_data.recipient,
            subject=notification_data.subject,
            content=notification_data.content,
            template_id=notification_data.template_id,
            template_data=notification_data.template_data,
            priority=notification_data.priority.value,
            max_retries=notification_data.max_retries,
            status=NotificationStatus.PENDING.value,
        )
        self.session.add(db_notification)
        await self.session.flush()
        await self.session.refresh(db_notification)
        return db_notification

    async def get_notification(self, notification_id: int) -> Optional[Notification]:
        """Get notification by ID"""
        query = select(Notification).where(Notification.id == notification_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_notifications_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
        notification_type: Optional[str] = None,
    ) -> tuple[list[Notification], int]:
        """Get notifications for a user with filters and total count"""
        query = select(Notification).where(Notification.user_id == user_id)

        # Apply filters
        if status:
            query = query.where(Notification.status == status)
        if notification_type:
            query = query.where(Notification.type == notification_type)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(desc(Notification.created_at))
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        notifications = list(result.scalars().all())

        return notifications, total

    async def get_pending_notifications(self, limit: int = 100) -> list[Notification]:
        """Get pending notifications for processing"""
        # Create a case statement for priority ordering (HIGH = 3, MEDIUM = 2, LOW = 1)
        from sqlalchemy import case

        priority_order = case(
            (Notification.priority == NotificationPriority.HIGH.value, 3),
            (Notification.priority == NotificationPriority.MEDIUM.value, 2),
            (Notification.priority == NotificationPriority.LOW.value, 1),
            else_=0,
        )

        query = (
            select(Notification)
            .where(Notification.status == NotificationStatus.PENDING.value)
            .order_by(
                desc(priority_order),  # Higher priority first
                asc(
                    Notification.created_at
                ),  # Older notifications first within same priority
            )
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_failed_notifications_for_retry(
        self, limit: int = 50
    ) -> list[Notification]:
        """Get failed notifications that can be retried"""
        query = (
            select(Notification)
            .where(
                and_(
                    Notification.status == NotificationStatus.FAILED.value,
                    Notification.retry_count < Notification.max_retries,
                )
            )
            .order_by(asc(Notification.failed_at))
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_notification(
        self, notification_id: int, update_data: NotificationUpdate
    ) -> Optional[Notification]:
        """Update notification"""
        notification = await self.get_notification(notification_id)
        if not notification:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            if hasattr(notification, field):
                setattr(notification, field, value)

        await self.session.flush()
        await self.session.refresh(notification)
        return notification

    async def mark_as_sent(
        self, notification_id: int, provider_response: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Mark notification as sent"""
        update_data = NotificationUpdate(
            status=SchemaNotificationStatus.SENT,
            sent_at=datetime.now(timezone.utc),
            provider_response=provider_response,
        )
        result = await self.update_notification(notification_id, update_data)
        return result is not None

    async def mark_as_delivered(
        self, notification_id: int, delivered_at: Optional[datetime] = None
    ) -> bool:
        """Mark notification as delivered"""
        if not delivered_at:
            delivered_at = datetime.now(timezone.utc)

        update_data = NotificationUpdate(
            status=SchemaNotificationStatus.DELIVERED, delivered_at=delivered_at
        )
        result = await self.update_notification(notification_id, update_data)
        return result is not None

    async def mark_as_failed(
        self, notification_id: int, failure_reason: str, increment_retry: bool = True
    ) -> bool:
        """Mark notification as failed"""
        notification = await self.get_notification(notification_id)
        if not notification:
            return False

        retry_count = notification.retry_count
        if increment_retry:
            retry_count += 1

        update_data = NotificationUpdate(
            status=SchemaNotificationStatus.FAILED,
            failed_at=datetime.now(timezone.utc),
            failure_reason=failure_reason,
            retry_count=retry_count,
        )
        result = await self.update_notification(notification_id, update_data)
        return result is not None

    async def get_notification_count_by_status(
        self, user_id: Optional[int] = None
    ) -> Dict[str, int]:
        """Get notification count grouped by status"""
        query = select(Notification.status, func.count(Notification.id).label("count"))

        if user_id:
            query = query.where(Notification.user_id == user_id)

        query = query.group_by(Notification.status)

        result = await self.session.execute(query)
        status_counts: Dict[str, int] = {}
        for row in result:
            status_counts[row[0]] = row[
                1
            ]  # Access by index since we're selecting specific columns
        return status_counts

    async def get_template(self, template_id: str) -> Optional[Template]:
        """Get notification template by ID"""
        query = select(Template).where(
            and_(Template.name == template_id, Template.is_active)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_templates_by_type(self, notification_type: str) -> list[Template]:
        """Get templates by notification type"""
        query = (
            select(Template)
            .where(and_(Template.type == notification_type, Template.is_active))
            .order_by(Template.name)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_notification(self, notification_id: int) -> bool:
        """Delete notification (soft delete by marking as cancelled)"""
        notification = await self.get_notification(notification_id)
        if not notification:
            return False

        # Instead of actual deletion, mark as cancelled
        notification.status = "cancelled"
        # updated_at will be set automatically by BaseModel

        await self.session.flush()
        return True
