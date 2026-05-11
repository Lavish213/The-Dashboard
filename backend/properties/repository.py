from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import PropertyStatus
from models.property import Property
from repositories.base import BaseRepository, PageResult


class PropertyRepository(BaseRepository[Property]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Property)

    async def get_by_status(self, status: PropertyStatus, page: int = 1, page_size: int = 20) -> PageResult[Property]:
        return await self.list_paginated(
            page=page, page_size=page_size,
            filters=[Property.property_status == status],
        )

    async def get_by_city_state(self, city: str, state: str, page: int = 1, page_size: int = 20) -> PageResult[Property]:
        return await self.list_paginated(
            page=page, page_size=page_size,
            filters=[Property.city == city, Property.state == state],
        )
