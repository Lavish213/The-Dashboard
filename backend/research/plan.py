"""
ResearchPlanRuntime — structured research plan lifecycle management.

Plans are checkpointable and approval-compatible.
Each revision increments the revision counter — creates a new record.
Idempotent on plan_key.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import ResearchEventType, ResearchPlanStatus
from models.research_plan import ResearchPlan
from repositories.research_event import ResearchEventRepository
from repositories.research_plan import ResearchPlanRepository
from research.contracts import (
    ResearchPlanRecord,
    ResearchPlanRevision,
    ResearchPlanSpec,
)


class ResearchPlanError(Exception):
    pass


class ResearchPlanRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._plans = ResearchPlanRepository(session)
        self._events = ResearchEventRepository(session)

    async def create(self, spec: ResearchPlanSpec) -> ResearchPlanRecord:
        """Create a plan. Idempotent on plan_key."""
        existing = await self._plans.get_by_key(spec.plan_key)
        if existing is not None:
            return self._to_record(existing)

        row = ResearchPlan(
            plan_key=spec.plan_key,
            job_id=spec.job_id,
            status=ResearchPlanStatus.draft,
            goal=spec.goal,
            steps=list(spec.steps),
            constraints=spec.constraints,
        )
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.plan_created,
            job_id=spec.job_id,
            payload={
                "plan_key": spec.plan_key,
                "goal": spec.goal,
                "step_count": len(spec.steps),
            },
        )
        return self._to_record(row)

    async def activate(
        self,
        plan_id: UUID,
        actor_id: UUID | None = None,
    ) -> ResearchPlanRecord:
        """Transition draft → active."""
        row = await self._plans.get_for_update(plan_id)
        if row is None:
            raise ResearchPlanError(f"Plan {plan_id} not found")
        if row.status != ResearchPlanStatus.draft:
            raise ResearchPlanError(
                f"Cannot activate plan with status {row.status}"
            )

        row.status = ResearchPlanStatus.active
        self._session.add(row)
        await self._session.flush()
        return self._to_record(row)

    async def revise(self, revision: ResearchPlanRevision) -> ResearchPlanRecord:
        """
        Revise a plan in place. Increments revision counter.
        Can only revise active or draft plans.
        """
        row = await self._plans.get_for_update(revision.plan_id)
        if row is None:
            raise ResearchPlanError(f"Plan {revision.plan_id} not found")
        if row.status not in (ResearchPlanStatus.draft, ResearchPlanStatus.active):
            raise ResearchPlanError(
                f"Cannot revise plan with status {row.status}"
            )

        row.revision += 1
        if revision.goal is not None:
            row.goal = revision.goal
        if revision.steps is not None:
            row.steps = list(revision.steps)
        if revision.constraints is not None:
            row.constraints = revision.constraints
        if row.status == ResearchPlanStatus.active:
            row.status = ResearchPlanStatus.revised

        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.plan_revised,
            job_id=row.job_id,
            actor_id=revision.actor_id,
            payload={"plan_id": str(revision.plan_id), "revision": row.revision},
        )
        return self._to_record(row)

    async def checkpoint(
        self,
        plan_id: UUID,
        state_blob: dict,
        actor_id: UUID | None = None,
    ) -> ResearchPlanRecord:
        """Persist checkpoint state without changing plan status."""
        row = await self._plans.get_for_update(plan_id)
        if row is None:
            raise ResearchPlanError(f"Plan {plan_id} not found")

        row.checkpoint_state = state_blob
        self._session.add(row)
        await self._session.flush()
        return self._to_record(row)

    async def complete(
        self,
        plan_id: UUID,
        actor_id: UUID | None = None,
    ) -> ResearchPlanRecord:
        """Transition active/revised → completed."""
        row = await self._plans.get_for_update(plan_id)
        if row is None:
            raise ResearchPlanError(f"Plan {plan_id} not found")
        if row.status not in (
            ResearchPlanStatus.active,
            ResearchPlanStatus.revised,
            ResearchPlanStatus.draft,
        ):
            raise ResearchPlanError(
                f"Cannot complete plan with status {row.status}"
            )

        row.status = ResearchPlanStatus.completed
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.plan_completed,
            job_id=row.job_id,
            actor_id=actor_id,
            payload={"plan_id": str(plan_id), "revision": row.revision},
        )
        return self._to_record(row)

    async def abandon(
        self,
        plan_id: UUID,
        actor_id: UUID | None = None,
    ) -> ResearchPlanRecord:
        """Transition any non-terminal status → abandoned."""
        row = await self._plans.get_for_update(plan_id)
        if row is None:
            raise ResearchPlanError(f"Plan {plan_id} not found")
        if row.status in (
            ResearchPlanStatus.completed,
            ResearchPlanStatus.abandoned,
        ):
            raise ResearchPlanError(
                f"Cannot abandon plan with status {row.status}"
            )

        row.status = ResearchPlanStatus.abandoned
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.plan_abandoned,
            job_id=row.job_id,
            actor_id=actor_id,
            payload={"plan_id": str(plan_id)},
        )
        return self._to_record(row)

    async def get(self, plan_id: UUID) -> ResearchPlanRecord | None:
        row = await self._plans.get(plan_id)
        return self._to_record(row) if row else None

    async def get_by_key(self, plan_key: str) -> ResearchPlanRecord | None:
        row = await self._plans.get_by_key(plan_key)
        return self._to_record(row) if row else None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _to_record(self, row: ResearchPlan) -> ResearchPlanRecord:
        return ResearchPlanRecord(
            plan_id=row.id,
            plan_key=row.plan_key,
            goal=row.goal,
            status=row.status,
            revision=row.revision,
            steps=row.steps,
            constraints=row.constraints,
            created_at=row.created_at,
            job_id=row.job_id,
            checkpoint_state=row.checkpoint_state,
            approval_id=row.approval_id,
        )
