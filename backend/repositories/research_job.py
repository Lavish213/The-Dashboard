"""
ResearchJobRepository — data access for research jobs.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import ResearchJobStatus
from models.research_job import ResearchJob


class ResearchJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, job_id: UUID) -> ResearchJob | None:
        result = await self._session.execute(
            select(ResearchJob).where(ResearchJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_by_key(self, job_key: str) -> ResearchJob | None:
        result = await self._session.execute(
            select(ResearchJob).where(ResearchJob.job_key == job_key)
        )
        return result.scalar_one_or_none()

    async def get_for_update(self, job_id: UUID) -> ResearchJob | None:
        result = await self._session.execute(
            select(ResearchJob)
            .where(ResearchJob.id == job_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def list_by_status(self, status: ResearchJobStatus) -> list[ResearchJob]:
        result = await self._session.execute(
            select(ResearchJob)
            .where(ResearchJob.status == status)
            .order_by(ResearchJob.created_at)
        )
        return list(result.scalars().all())

    async def list_by_session(self, sophia_session_id: UUID) -> list[ResearchJob]:
        result = await self._session.execute(
            select(ResearchJob)
            .where(ResearchJob.sophia_session_id == sophia_session_id)
            .order_by(ResearchJob.created_at)
        )
        return list(result.scalars().all())
