"""
ResearchEventRepository — append-only event log for the research runtime.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import ResearchEventType
from models.research_event import ResearchEvent


class ResearchEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        event_type: ResearchEventType,
        *,
        job_id: UUID | None = None,
        task_id: UUID | None = None,
        actor_id: UUID | None = None,
        correlation_id: str | None = None,
        payload: dict | None = None,
    ) -> ResearchEvent:
        event = ResearchEvent(
            event_type=event_type,
            job_id=job_id,
            task_id=task_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            payload=payload or {},
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def get_for_job(self, job_id: UUID) -> list[ResearchEvent]:
        result = await self._session.execute(
            select(ResearchEvent)
            .where(ResearchEvent.job_id == job_id)
            .order_by(ResearchEvent.emitted_at)
        )
        return list(result.scalars().all())

    async def get_for_task(self, task_id: UUID) -> list[ResearchEvent]:
        result = await self._session.execute(
            select(ResearchEvent)
            .where(ResearchEvent.task_id == task_id)
            .order_by(ResearchEvent.emitted_at)
        )
        return list(result.scalars().all())

    async def get_by_type(
        self,
        event_type: ResearchEventType,
        job_id: UUID | None = None,
    ) -> list[ResearchEvent]:
        q = select(ResearchEvent).where(ResearchEvent.event_type == event_type)
        if job_id is not None:
            q = q.where(ResearchEvent.job_id == job_id)
        q = q.order_by(ResearchEvent.emitted_at)
        result = await self._session.execute(q)
        return list(result.scalars().all())
