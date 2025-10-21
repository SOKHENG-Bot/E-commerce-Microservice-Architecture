from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from user_service.app.models.address import Address, AddressTypeEnum


class AddressRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: Address) -> Address:
        self.session.add(data)
        await self.session.commit()
        await self.session.refresh(data)
        return data

    async def update(self, data: Address) -> Address:
        # Use merge instead of add for updates
        merged = await self.session.merge(data)
        await self.session.commit()
        await self.session.refresh(merged)
        return merged

    async def delete(self, data: Address) -> None:
        await self.session.delete(data)
        await self.session.commit()

    async def get_address_by_id(self, address_id: int) -> Optional[Address]:
        """Get address by ID"""
        result = await self.session.execute(
            select(Address).where(Address.id == address_id)
        )
        return result.scalar_one_or_none()

    async def unset_default_addresses(
        self, user_id: int, address_type: AddressTypeEnum
    ) -> None:
        """Unset all default addresses of a specific type for a user"""
        result = await self.session.execute(
            select(Address).where(
                Address.user_id == user_id,
                Address.type == address_type,
                Address.is_default,
            )
        )
        addresses = result.scalars().all()

        for address in addresses:
            address.is_default = False

        await self.session.commit()

    async def get_addresses_by_type(
        self, user_id: int, address_type: AddressTypeEnum
    ) -> List[Address]:
        """Get all addresses of specific type for a user"""
        result = await self.session.execute(
            select(Address)
            .where(Address.user_id == user_id, Address.type == address_type)
            .order_by(Address.is_default.desc(), Address.created_at)
        )
        return list(result.scalars().all())
