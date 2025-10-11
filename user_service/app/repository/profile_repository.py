from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from user_service.app.models.profile import Profile


class ProfileRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_profile(self, user_id: int) -> Optional[Profile]:
        result = await self.session.execute(
            select(Profile).where(Profile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: Profile) -> Profile:
        self.session.add(data)
        await self.session.commit()
        await self.session.refresh(data)
        return data

    async def update(self, data: Profile) -> Profile:
        await self.session.commit()
        await self.session.refresh(data)
        return data

    async def delete(self, data: Profile) -> None:
        await self.session.delete(data)
        await self.session.commit()
