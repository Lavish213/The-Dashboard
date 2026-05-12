from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.audit_log import AuditLog
from repositories.base import BaseRepository, PageResult


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, AuditLog)

    async def get_by_target(
        self, target_type: str, target_id: UUID,
        page: int = 1, page_size: int = 20,
    ) -> PageResult[AuditLog]:
        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=[
                AuditLog.target_type == target_type,
                AuditLog.target_id == target_id,
            ],
            order_by=AuditLog.created_at.desc(),
        )

    async def get_by_actor(
        self, actor_id: UUID, page: int = 1, page_size: int = 20,
    ) -> PageResult[AuditLog]:
        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=[AuditLog.actor_id == actor_id],
            order_by=AuditLog.created_at.desc(),
        )

    async def get_by_correlation(
        self, correlation_id: UUID, page: int = 1, page_size: int = 50,
    ) -> PageResult[AuditLog]:
        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=[AuditLog.correlation_id == correlation_id],
            order_by=AuditLog.created_at.asc(),
        )

    async def get_timeline(
        self,
        page: int = 1,
        page_size: int = 50,
        actor_id: UUID | None = None,
        target_type: str | None = None,
        target_id: UUID | None = None,
        action: str | None = None,
    ) -> PageResult[AuditLog]:
        """Cross-entity unified timeline feed with optional filters."""
        filters = []
        if actor_id is not None:
            filters.append(AuditLog.actor_id == actor_id)
        if target_type is not None:
            filters.append(AuditLog.target_type == target_type)
        if target_id is not None:
            filters.append(AuditLog.target_id == target_id)
        if action is not None:
            filters.append(AuditLog.action == action)
        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=filters or None,
            order_by=AuditLog.created_at.desc(),
        )
