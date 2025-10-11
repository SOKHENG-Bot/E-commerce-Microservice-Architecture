"""
Permission Service - Core Functions Only
Business logic for essential user permission and role checking.
"""

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from user_service.app.models.user import Role, User


class PermissionService:
    """Service for checking user permissions and roles"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def has_permission(self, user_id: int, permission_name: str) -> bool:
        """
        Check if a user has a specific permission (through their roles).
        """
        try:
            # Get user with their roles and permissions
            query = (
                select(User)
                .where(User.id == user_id)
                .options(selectinload(User.roles).selectinload(Role.permissions))
            )
            result = await self.session.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                return False

            # Check permissions through roles
            for role in user.roles:
                for permission in role.permissions:
                    if permission.name == permission_name:
                        return True

            return False

        except Exception:
            return False

    async def get_user_permissions(self, user_id: int) -> List[str]:
        """
        Get all permissions for a user (through their roles).
        """
        try:
            # Get user with their roles and permissions
            query = (
                select(User)
                .where(User.id == user_id)
                .options(selectinload(User.roles).selectinload(Role.permissions))
            )
            result = await self.session.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                return []

            # Collect all permissions
            permissions: set[str] = set()
            for role in user.roles:
                for permission in role.permissions:
                    permissions.add(permission.name)

            return list(permissions)

        except Exception:
            return []

    async def get_user_roles(self, user_id: int) -> List[str]:
        """
        Get all roles for a user.
        """
        try:
            # Get user with their roles
            query = (
                select(User).where(User.id == user_id).options(selectinload(User.roles))
            )
            result = await self.session.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                return []

            # Collect all role names
            return [role.name for role in user.roles]

        except Exception:
            return []
