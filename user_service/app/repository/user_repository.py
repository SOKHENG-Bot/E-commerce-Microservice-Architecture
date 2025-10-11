from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from user_service.app.models.user import Role, User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def query_info(self, user_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.profile),
                selectinload(User.addresses),
                selectinload(User.roles).selectinload(Role.permissions),
            )
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def query_id(self, user_id: int) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def query_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, user_data: User) -> User:
        self.session.add(user_data)
        await self.session.commit()
        await self.session.refresh(user_data)
        return user_data

    async def update(self, user_data: User) -> User:
        await self.session.commit()
        await self.session.refresh(user_data)
        return user_data

    async def delete(self, user_data: User) -> None:
        await self.session.delete(user_data)
        await self.session.commit()
