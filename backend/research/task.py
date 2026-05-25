"""
ResearchTaskRuntime — lifecycle management for individual research tasks.

State transitions:
  pending   → running / cancelled / skipped
  running   → completed / failed / cancelled
  failed    → running  (retry, if retry_count < max_retries)
  blocked   → pending  (when upstreams complete)

All transitions emit ResearchEvents.
Token accounting flows up to the parent job.
Idempotent on task_key.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import ResearchEventType, ResearchTaskStatus
from models.research_task import ResearchTask
from repositories.research_event import ResearchEventRepository
from repositories.research_task import ResearchTaskRepository
from research.contracts import ResearchTaskRecord, ResearchTaskSpec


class ResearchTaskError(Exception):
    pass


class ResearchTaskRetryExhaustedError(ResearchTaskError):
    pass


_VALID_TRANSITIONS: dict[ResearchTaskStatus, set[ResearchTaskStatus]] = {
    ResearchTaskStatus.pending: {
        ResearchTaskStatus.running,
        ResearchTaskStatus.cancelled,
        ResearchTaskStatus.skipped,
        ResearchTaskStatus.blocked,
    },
    ResearchTaskStatus.blocked: {
        ResearchTaskStatus.pending,
        ResearchTaskStatus.cancelled,
    },
    ResearchTaskStatus.running: {
        ResearchTaskStatus.completed,
        ResearchTaskStatus.failed,
        ResearchTaskStatus.cancelled,
    },
    ResearchTaskStatus.failed: {
        ResearchTaskStatus.running,  # retry
        ResearchTaskStatus.cancelled,
    },
    ResearchTaskStatus.completed: set(),
    ResearchTaskStatus.cancelled: set(),
    ResearchTaskStatus.skipped: set(),
}


class ResearchTaskRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tasks = ResearchTaskRepository(session)
        self._events = ResearchEventRepository(session)

    async def create(self, spec: ResearchTaskSpec) -> ResearchTaskRecord:
        """Create a task. Idempotent on task_key."""
        if spec.task_key:
            existing = await self._tasks.get_by_key(spec.task_key)
            if existing:
                return self._to_record(existing)

        row = ResearchTask(
            job_id=spec.job_id,
            task_index=spec.task_index,
            task_type=spec.task_type,
            input_payload=spec.input_payload,
            depth=spec.depth,
            max_retries=spec.max_retries,
            task_key=spec.task_key,
        )
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.task_created,
            job_id=spec.job_id,
            task_id=row.id,
            payload={"task_index": spec.task_index, "task_type": spec.task_type},
        )
        return self._to_record(row)

    async def start(
        self,
        task_id: UUID,
        actor_id: UUID | None = None,
    ) -> ResearchTaskRecord:
        """Transition pending/blocked → running."""
        row = await self._tasks.get_for_update(task_id)
        if row is None:
            raise ResearchTaskError(f"Task {task_id} not found")
        self._assert_transition(row.status, ResearchTaskStatus.running)

        row.status = ResearchTaskStatus.running
        row.started_at = datetime.now(UTC)
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.task_started,
            job_id=row.job_id,
            task_id=task_id,
            actor_id=actor_id,
            payload={"task_index": row.task_index},
        )
        return self._to_record(row)

    async def complete(
        self,
        task_id: UUID,
        output_payload: dict,
        tokens_input: int = 0,
        tokens_output: int = 0,
        actor_id: UUID | None = None,
    ) -> ResearchTaskRecord:
        """Transition running → completed. Increments job token + task counters."""
        row = await self._tasks.get_for_update(task_id)
        if row is None:
            raise ResearchTaskError(f"Task {task_id} not found")
        self._assert_transition(row.status, ResearchTaskStatus.completed)

        row.status = ResearchTaskStatus.completed
        row.output_payload = output_payload
        row.tokens_input = tokens_input
        row.tokens_output = tokens_output
        row.completed_at = datetime.now(UTC)
        self._session.add(row)
        await self._session.flush()

        # Atomically increment job token + task counters
        await self._session.execute(
            text(
                "UPDATE research_jobs "
                "SET tokens_used = tokens_used + :delta, "
                "    completed_task_count = completed_task_count + 1 "
                "WHERE id = :job_id"
            ),
            {"delta": tokens_input + tokens_output, "job_id": row.job_id},
        )

        await self._events.append(
            ResearchEventType.task_completed,
            job_id=row.job_id,
            task_id=task_id,
            actor_id=actor_id,
            payload={
                "task_index": row.task_index,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
            },
        )
        return self._to_record(row)

    async def fail(
        self,
        task_id: UUID,
        error: str,
        actor_id: UUID | None = None,
    ) -> ResearchTaskRecord:
        """Transition running → failed."""
        row = await self._tasks.get_for_update(task_id)
        if row is None:
            raise ResearchTaskError(f"Task {task_id} not found")
        self._assert_transition(row.status, ResearchTaskStatus.failed)

        row.status = ResearchTaskStatus.failed
        row.error = error
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.task_failed,
            job_id=row.job_id,
            task_id=task_id,
            actor_id=actor_id,
            payload={"error": error, "task_index": row.task_index},
        )
        return self._to_record(row)

    async def retry(
        self,
        task_id: UUID,
        actor_id: UUID | None = None,
    ) -> ResearchTaskRecord:
        """
        Transition failed → running (retry).
        Raises ResearchTaskRetryExhaustedError if retry_count >= max_retries.
        """
        row = await self._tasks.get_for_update(task_id)
        if row is None:
            raise ResearchTaskError(f"Task {task_id} not found")
        if row.retry_count >= row.max_retries:
            raise ResearchTaskRetryExhaustedError(
                f"Task {task_id} exhausted retries ({row.max_retries})"
            )
        self._assert_transition(row.status, ResearchTaskStatus.running)

        row.status = ResearchTaskStatus.running
        row.retry_count += 1
        row.error = None
        row.started_at = datetime.now(UTC)
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.task_retried,
            job_id=row.job_id,
            task_id=task_id,
            actor_id=actor_id,
            payload={"retry_count": row.retry_count, "max_retries": row.max_retries},
        )
        return self._to_record(row)

    async def cancel(
        self,
        task_id: UUID,
        actor_id: UUID | None = None,
    ) -> ResearchTaskRecord:
        """Transition pending/running/failed → cancelled."""
        row = await self._tasks.get_for_update(task_id)
        if row is None:
            raise ResearchTaskError(f"Task {task_id} not found")
        self._assert_transition(row.status, ResearchTaskStatus.cancelled)

        row.status = ResearchTaskStatus.cancelled
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.task_cancelled,
            job_id=row.job_id,
            task_id=task_id,
            actor_id=actor_id,
            payload={"task_index": row.task_index},
        )
        return self._to_record(row)

    async def skip(
        self,
        task_id: UUID,
        actor_id: UUID | None = None,
    ) -> ResearchTaskRecord:
        """Transition pending → skipped (governance blocked or dependency pruned)."""
        row = await self._tasks.get_for_update(task_id)
        if row is None:
            raise ResearchTaskError(f"Task {task_id} not found")
        self._assert_transition(row.status, ResearchTaskStatus.skipped)

        row.status = ResearchTaskStatus.skipped
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.task_skipped,
            job_id=row.job_id,
            task_id=task_id,
            actor_id=actor_id,
            payload={"task_index": row.task_index},
        )
        return self._to_record(row)

    async def get(self, task_id: UUID) -> ResearchTaskRecord | None:
        row = await self._tasks.get(task_id)
        return self._to_record(row) if row else None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _assert_transition(
        self,
        current: ResearchTaskStatus,
        target: ResearchTaskStatus,
    ) -> None:
        allowed = _VALID_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ResearchTaskError(
                f"Invalid task transition: {current} → {target}"
            )

    def _to_record(self, row: ResearchTask) -> ResearchTaskRecord:
        return ResearchTaskRecord(
            task_id=row.id,
            job_id=row.job_id,
            task_index=row.task_index,
            task_type=row.task_type,
            status=row.status,
            input_payload=row.input_payload,
            depth=row.depth,
            retry_count=row.retry_count,
            max_retries=row.max_retries,
            tokens_input=row.tokens_input,
            tokens_output=row.tokens_output,
            created_at=row.created_at,
            task_key=row.task_key,
            output_payload=row.output_payload,
            error=row.error,
            governance_verdict=row.governance_verdict,
            approval_id=row.approval_id,
            started_at=row.started_at,
            completed_at=row.completed_at,
        )
