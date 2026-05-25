from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.approval import Approval
from models.enums import ApprovalStatus, ApprovalType
from repositories.base import BaseRepository, PageResult


class ApprovalRepository(BaseRepository[Approval]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Approval)

    async def get_for_update(self, approval_id: UUID) -> Approval | None:
        """Fetch with SELECT FOR UPDATE — holds row lock until transaction end."""
        result = await self.session.execute(
            select(Approval)
            .where(Approval.id == approval_id, Approval.deleted_at.is_(None))
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_for_update_or_raise(self, approval_id: UUID) -> Approval:
        from core.exceptions import NotFoundError
        approval = await self.get_for_update(approval_id)
        if approval is None:
            raise NotFoundError(Approval.__tablename__, str(approval_id))
        return approval

    async def get_pending(self, page: int = 1, page_size: int = 20) -> PageResult[Approval]:
        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=[Approval.approval_status == ApprovalStatus.pending],
        )

    async def get_pending_by_type(
        self,
        approval_type: ApprovalType,
        page: int = 1,
        page_size: int = 20,
    ) -> PageResult[Approval]:
        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=[
                Approval.approval_status == ApprovalStatus.pending,
                Approval.approval_type == approval_type,
            ],
        )

    async def get_expired_pending(self) -> list[Approval]:
        """Return all pending approvals whose expires_at is in the past."""
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(Approval).where(
                Approval.approval_status == ApprovalStatus.pending,
                Approval.expires_at.is_not(None),
                Approval.expires_at < now,
                Approval.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def get_escalated(self, page: int = 1, page_size: int = 20) -> PageResult[Approval]:
        """Return all escalated approvals (still require resolution)."""
        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=[Approval.approval_status == ApprovalStatus.escalated],
        )

    async def get_by_workflow(self, workflow_id: UUID) -> list[Approval]:
        result = await self.session.execute(
            select(Approval).where(
                Approval.workflow_id == workflow_id,
                Approval.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())
