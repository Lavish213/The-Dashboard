from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import LeadStatus
from models.lead import Lead
from repositories.base import BaseRepository, PageResult


class LeadRepository(BaseRepository[Lead]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Lead)

    async def get_by_phone(self, phone: str) -> Lead | None:
        result = await self.session.execute(
            select(Lead).where(Lead.phone == phone, Lead.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_status(self, status: LeadStatus, page: int = 1, page_size: int = 20) -> PageResult[Lead]:
        return await self.list_paginated(
            page=page, page_size=page_size,
            filters=[Lead.lead_status == status],
            order_by=Lead.created_at.desc(),
        )

    async def get_by_assigned_user(self, user_id: UUID, page: int = 1, page_size: int = 20) -> PageResult[Lead]:
        return await self.list_paginated(
            page=page, page_size=page_size,
            filters=[Lead.assigned_user_id == user_id],
            order_by=Lead.created_at.desc(),
        )
