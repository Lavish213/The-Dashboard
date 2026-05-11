from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.call import Call
from models.enums import CallStatus
from repositories.base import BaseRepository, PageResult


class CallRepository(BaseRepository[Call]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Call)

    async def get_by_lead(self, lead_id: UUID, page: int = 1, page_size: int = 20) -> PageResult[Call]:
        return await self.list_paginated(
            page=page, page_size=page_size,
            filters=[Call.lead_id == lead_id],
            order_by=Call.created_at.desc(),
        )

    async def get_by_status(self, status: CallStatus, page: int = 1, page_size: int = 20) -> PageResult[Call]:
        return await self.list_paginated(
            page=page, page_size=page_size,
            filters=[Call.call_status == status],
        )
