"""
ResearchJobRuntime — state machine for research job lifecycle.

State transitions:
  queued    → running
  running   → paused / completed / failed / cancelled
  paused    → running / cancelled

All transitions emit ResearchEvents. Idempotent on job_key.
Checkpoint blob persisted on pause.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import ResearchEventType, ResearchJobStatus
from models.research_job import ResearchJob
from repositories.research_event import ResearchEventRepository
from repositories.research_job import ResearchJobRepository
from research.contracts import ResearchJobRecord, ResearchJobSpec


class ResearchJobError(Exception):
    pass


_VALID_TRANSITIONS: dict[ResearchJobStatus, set[ResearchJobStatus]] = {
    ResearchJobStatus.queued: {ResearchJobStatus.running, ResearchJobStatus.cancelled},
    ResearchJobStatus.running: {
        ResearchJobStatus.paused,
        ResearchJobStatus.completed,
        ResearchJobStatus.failed,
        ResearchJobStatus.cancelled,
    },
    ResearchJobStatus.paused: {ResearchJobStatus.running, ResearchJobStatus.cancelled},
    ResearchJobStatus.completed: set(),
    ResearchJobStatus.failed: set(),
    ResearchJobStatus.cancelled: set(),
}


class ResearchJobRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jobs = ResearchJobRepository(session)
        self._events = ResearchEventRepository(session)

    async def create(self, spec: ResearchJobSpec) -> ResearchJobRecord:
        """Create or return existing job. Idempotent on job_key."""
        existing = await self._jobs.get_by_key(spec.job_key)
        if existing is not None:
            return self._to_record(existing)

        row = ResearchJob(
            job_key=spec.job_key,
            status=ResearchJobStatus.queued,
            token_budget=spec.token_budget,
            max_depth=spec.max_depth,
            sophia_session_id=spec.sophia_session_id,
            workflow_id=spec.workflow_id,
            initiated_by=spec.initiated_by,
            plan_id=spec.plan_id,
            job_metadata=spec.job_metadata,
        )
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.job_created,
            job_id=row.id,
            actor_id=spec.initiated_by,
            payload={
                "job_key": spec.job_key,
                "token_budget": spec.token_budget,
                "max_depth": spec.max_depth,
            },
        )
        return self._to_record(row)

    async def start(
        self,
        job_id: UUID,
        actor_id: UUID | None = None,
    ) -> ResearchJobRecord:
        """Transition queued → running."""
        row = await self._jobs.get_for_update(job_id)
        if row is None:
            raise ResearchJobError(f"Job {job_id} not found")
        self._assert_transition(row.status, ResearchJobStatus.running)

        row.status = ResearchJobStatus.running
        row.started_at = datetime.now(UTC)
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.job_started,
            job_id=job_id,
            actor_id=actor_id,
            payload={"started_at": row.started_at.isoformat()},
        )
        return self._to_record(row)

    async def pause(
        self,
        job_id: UUID,
        checkpoint_state: dict | None = None,
        actor_id: UUID | None = None,
    ) -> ResearchJobRecord:
        """Transition running → paused. Persists checkpoint blob."""
        row = await self._jobs.get_for_update(job_id)
        if row is None:
            raise ResearchJobError(f"Job {job_id} not found")
        self._assert_transition(row.status, ResearchJobStatus.paused)

        row.status = ResearchJobStatus.paused
        row.paused_at = datetime.now(UTC)
        if checkpoint_state is not None:
            row.checkpoint_state = checkpoint_state
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.job_paused,
            job_id=job_id,
            actor_id=actor_id,
            payload={"has_checkpoint": checkpoint_state is not None},
        )
        return self._to_record(row)

    async def resume(
        self,
        job_id: UUID,
        actor_id: UUID | None = None,
    ) -> ResearchJobRecord:
        """Transition paused → running."""
        row = await self._jobs.get_for_update(job_id)
        if row is None:
            raise ResearchJobError(f"Job {job_id} not found")
        self._assert_transition(row.status, ResearchJobStatus.running)

        row.status = ResearchJobStatus.running
        row.paused_at = None
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.job_resumed,
            job_id=job_id,
            actor_id=actor_id,
            payload={},
        )
        return self._to_record(row)

    async def complete(
        self,
        job_id: UUID,
        actor_id: UUID | None = None,
    ) -> ResearchJobRecord:
        """Transition running → completed."""
        row = await self._jobs.get_for_update(job_id)
        if row is None:
            raise ResearchJobError(f"Job {job_id} not found")
        self._assert_transition(row.status, ResearchJobStatus.completed)

        row.status = ResearchJobStatus.completed
        row.completed_at = datetime.now(UTC)
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.job_completed,
            job_id=job_id,
            actor_id=actor_id,
            payload={
                "task_count": row.task_count,
                "tokens_used": row.tokens_used,
            },
        )
        return self._to_record(row)

    async def fail(
        self,
        job_id: UUID,
        error: str,
        actor_id: UUID | None = None,
    ) -> ResearchJobRecord:
        """Transition running → failed."""
        row = await self._jobs.get_for_update(job_id)
        if row is None:
            raise ResearchJobError(f"Job {job_id} not found")
        self._assert_transition(row.status, ResearchJobStatus.failed)

        row.status = ResearchJobStatus.failed
        row.error = error
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.job_failed,
            job_id=job_id,
            actor_id=actor_id,
            payload={"error": error},
        )
        return self._to_record(row)

    async def cancel(
        self,
        job_id: UUID,
        reason: str,
        actor_id: UUID | None = None,
    ) -> ResearchJobRecord:
        """Transition queued/running/paused → cancelled."""
        row = await self._jobs.get_for_update(job_id)
        if row is None:
            raise ResearchJobError(f"Job {job_id} not found")
        self._assert_transition(row.status, ResearchJobStatus.cancelled)

        row.status = ResearchJobStatus.cancelled
        row.cancel_reason = reason
        row.cancelled_at = datetime.now(UTC)
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.job_cancelled,
            job_id=job_id,
            actor_id=actor_id,
            payload={"reason": reason},
        )
        return self._to_record(row)

    async def checkpoint(
        self,
        job_id: UUID,
        state_blob: dict,
        actor_id: UUID | None = None,
    ) -> ResearchJobRecord:
        """Persist checkpoint without changing status (running jobs can checkpoint)."""
        row = await self._jobs.get_for_update(job_id)
        if row is None:
            raise ResearchJobError(f"Job {job_id} not found")

        row.checkpoint_state = state_blob
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.job_checkpointed,
            job_id=job_id,
            actor_id=actor_id,
            payload={"task_count": row.task_count, "tokens_used": row.tokens_used},
        )
        return self._to_record(row)

    async def get(self, job_id: UUID) -> ResearchJobRecord | None:
        row = await self._jobs.get(job_id)
        return self._to_record(row) if row else None

    async def get_by_key(self, job_key: str) -> ResearchJobRecord | None:
        row = await self._jobs.get_by_key(job_key)
        return self._to_record(row) if row else None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _assert_transition(
        self,
        current: ResearchJobStatus,
        target: ResearchJobStatus,
    ) -> None:
        allowed = _VALID_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ResearchJobError(
                f"Invalid job transition: {current} → {target}"
            )

    def _to_record(self, row: ResearchJob) -> ResearchJobRecord:
        return ResearchJobRecord(
            job_id=row.id,
            job_key=row.job_key,
            status=row.status,
            token_budget=row.token_budget,
            tokens_used=row.tokens_used,
            task_count=row.task_count,
            completed_task_count=row.completed_task_count,
            max_depth=row.max_depth,
            current_depth=row.current_depth,
            checkpoint_state=row.checkpoint_state,
            job_metadata=row.job_metadata,
            created_at=row.created_at,
            sophia_session_id=row.sophia_session_id,
            workflow_id=row.workflow_id,
            initiated_by=row.initiated_by,
            plan_id=row.plan_id,
            cancel_reason=row.cancel_reason,
            error=row.error,
            started_at=row.started_at,
            paused_at=row.paused_at,
            completed_at=row.completed_at,
            cancelled_at=row.cancelled_at,
        )
