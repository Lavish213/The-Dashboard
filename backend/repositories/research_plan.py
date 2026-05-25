"""
ResearchPlanRepository — data access for research plans.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.research_plan import ResearchPlan


class ResearchPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, plan_id: UUID) -> ResearchPlan | None:
        result = await self._session.execute(
            select(ResearchPlan).where(ResearchPlan.id == plan_id)
        )
        return result.scalar_one_or_none()

    async def get_by_key(self, plan_key: str) -> ResearchPlan | None:
        result = await self._session.execute(
            select(ResearchPlan).where(ResearchPlan.plan_key == plan_key)
        )
        return result.scalar_one_or_none()

    async def get_for_update(self, plan_id: UUID) -> ResearchPlan | None:
        result = await self._session.execute(
            select(ResearchPlan)
            .where(ResearchPlan.id == plan_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def list_by_job(self, job_id: UUID) -> list[ResearchPlan]:
        result = await self._session.execute(
            select(ResearchPlan)
            .where(ResearchPlan.job_id == job_id)
            .order_by(ResearchPlan.created_at)
        )
        return list(result.scalars().all())
