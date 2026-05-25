"""
ResearchTaskRepository — data access for research tasks and dependencies.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import ResearchTaskStatus
from models.research_task import ResearchTask
from models.research_task_dependency import ResearchTaskDependency


class ResearchTaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, task_id: UUID) -> ResearchTask | None:
        result = await self._session.execute(
            select(ResearchTask).where(ResearchTask.id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_by_key(self, task_key: str) -> ResearchTask | None:
        result = await self._session.execute(
            select(ResearchTask).where(ResearchTask.task_key == task_key)
        )
        return result.scalar_one_or_none()

    async def get_for_update(self, task_id: UUID) -> ResearchTask | None:
        result = await self._session.execute(
            select(ResearchTask)
            .where(ResearchTask.id == task_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def list_by_job(self, job_id: UUID) -> list[ResearchTask]:
        result = await self._session.execute(
            select(ResearchTask)
            .where(ResearchTask.job_id == job_id)
            .order_by(ResearchTask.task_index)
        )
        return list(result.scalars().all())

    async def list_by_status(
        self,
        job_id: UUID,
        status: ResearchTaskStatus,
    ) -> list[ResearchTask]:
        result = await self._session.execute(
            select(ResearchTask)
            .where(
                ResearchTask.job_id == job_id,
                ResearchTask.status == status,
            )
            .order_by(ResearchTask.task_index)
        )
        return list(result.scalars().all())

    async def add_dependency(
        self,
        job_id: UUID,
        upstream_task_id: UUID,
        downstream_task_id: UUID,
    ) -> ResearchTaskDependency:
        dep = ResearchTaskDependency(
            job_id=job_id,
            upstream_task_id=upstream_task_id,
            downstream_task_id=downstream_task_id,
        )
        self._session.add(dep)
        await self._session.flush()
        return dep

    async def get_dependencies(self, job_id: UUID) -> list[ResearchTaskDependency]:
        result = await self._session.execute(
            select(ResearchTaskDependency).where(
                ResearchTaskDependency.job_id == job_id
            )
        )
        return list(result.scalars().all())

    async def get_upstreams(self, task_id: UUID) -> list[ResearchTaskDependency]:
        """Return all edges where task_id is the downstream (i.e., its prerequisites)."""
        result = await self._session.execute(
            select(ResearchTaskDependency).where(
                ResearchTaskDependency.downstream_task_id == task_id
            )
        )
        return list(result.scalars().all())
