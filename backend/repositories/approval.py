from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.approval import Approval
from models.enums import ApprovalStatus
from repositories.base import BaseRepository, PageResult


class ApprovalRepository(BaseRepository[Approval]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Approval)

    async def get_pending(self, page: int = 1, page_size: int = 20) -> PageResult[Approval]:
        return await self.list_paginated(
            page=page, page_size=page_size,
            filters=[Approval.approval_status == ApprovalStatus.pending],
        )

    async def get_by_workflow(self, workflow_id: UUID) -> list[Approval]:
        result = await self.session.execute(
            select(Approval).where(
                Approval.workflow_id == workflow_id,
                Approval.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())
