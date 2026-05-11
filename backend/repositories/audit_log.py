from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.audit_log import AuditLog
from repositories.base import BaseRepository, PageResult


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, AuditLog)

    async def get_by_target(
        self, target_type: str, target_id: UUID,
        page: int = 1, page_size: int = 20
    ) -> PageResult[AuditLog]:
        return await self.list_paginated(
            page=page, page_size=page_size,
            filters=[
                AuditLog.target_type == target_type,
                AuditLog.target_id == target_id,
            ],
            order_by=AuditLog.created_at.desc(),
        )

    async def get_by_actor(
        self, actor_id: UUID, page: int = 1, page_size: int = 20
    ) -> PageResult[AuditLog]:
        return await self.list_paginated(
            page=page, page_size=page_size,
            filters=[AuditLog.actor_id == actor_id],
            order_by=AuditLog.created_at.desc(),
        )
