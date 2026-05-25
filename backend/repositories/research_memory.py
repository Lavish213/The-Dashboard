"""
ResearchMemoryRepository — data access for scoped research memory.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import ResearchMemoryScope
from models.research_memory import ResearchMemory


class ResearchMemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        job_id: UUID,
        scope: ResearchMemoryScope,
        memory_key: str,
        task_id: UUID | None = None,
    ) -> ResearchMemory | None:
        q = select(ResearchMemory).where(
            ResearchMemory.job_id == job_id,
            ResearchMemory.scope == scope,
            ResearchMemory.memory_key == memory_key,
        )
        if task_id is not None:
            q = q.where(ResearchMemory.task_id == task_id)
        else:
            q = q.where(ResearchMemory.task_id.is_(None))
        result = await self._session.execute(q)
        return result.scalar_one_or_none()

    async def list_by_job(self, job_id: UUID) -> list[ResearchMemory]:
        result = await self._session.execute(
            select(ResearchMemory)
            .where(ResearchMemory.job_id == job_id)
            .order_by(ResearchMemory.created_at)
        )
        return list(result.scalars().all())

    async def list_by_scope(
        self,
        job_id: UUID,
        scope: ResearchMemoryScope,
        task_id: UUID | None = None,
    ) -> list[ResearchMemory]:
        q = select(ResearchMemory).where(
            ResearchMemory.job_id == job_id,
            ResearchMemory.scope == scope,
        )
        if task_id is not None:
            q = q.where(ResearchMemory.task_id == task_id)
        result = await self._session.execute(q.order_by(ResearchMemory.created_at))
        return list(result.scalars().all())

    async def delete_for_job(self, job_id: UUID) -> int:
        """Hard-delete all memory entries for a job. Returns count deleted."""
        result = await self._session.execute(
            delete(ResearchMemory).where(ResearchMemory.job_id == job_id)
        )
        return result.rowcount

    async def delete_expired(self) -> int:
        """Hard-delete all expired memory entries. Returns count deleted."""
        now = datetime.now(UTC)
        result = await self._session.execute(
            delete(ResearchMemory).where(
                ResearchMemory.expires_at.is_not(None),
                ResearchMemory.expires_at <= now,
            )
        )
        return result.rowcount
