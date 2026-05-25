"""
RetryCoordinator — persistent retry orchestration for failed workflows.

Wraps pure retries.py (stateless) with DB-backed audit via workflow_events.
Retry state is reconstructed from the latest EVT_RETRY_SCHEDULED event.

Invariants:
- All state changes emit workflow_events for full audit trail
- Exhaustion triggers dead-letter + raises RetryExhaustedError
- get_due() returns workflows where next_retry_at <= now and status = failed
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from events.contracts import DomainEvent
from events.emitter import event_emitter
from models.enums import AuditActorType, WorkflowStatus
from models.workflow_event import WorkflowEvent
from workflows.deadletter import DeadLetterRuntime
from workflows.persistence import WorkflowEventRepository, WorkflowRepository
from workflows.retries import (
    RetryExhaustedError,
    RetryPolicy,
    RetryState,
    record_failure,
)

logger = structlog.get_logger(__name__)

RETRY_CHANNEL = "workflows"
EVT_RETRY_SCHEDULED = "workflow.retry.scheduled"
EVT_RETRY_ATTEMPTED = "workflow.retry.attempted"
EVT_RETRY_EXHAUSTED = "workflow.retry.exhausted"


@dataclass(frozen=True)
class ScheduledRetry:
    workflow_id: UUID
    attempt: int
    next_retry_at: datetime
    last_error: str


class RetryCoordinator:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)
        self._events = WorkflowEventRepository(session)
        self._dead_letter = DeadLetterRuntime(session)

    async def schedule(
        self,
        workflow_id: UUID,
        error: str,
        policy: RetryPolicy | None = None,
    ) -> ScheduledRetry:
        """
        Schedule retry for a failed workflow.
        Reads current attempt count from events, computes next retry via policy.
        Raises RetryExhaustedError (and records dead-letter) when limit reached.
        """
        retry_policy = policy or RetryPolicy()
        current_state = await self._get_current_state(workflow_id)

        try:
            new_state = record_failure(current_state, retry_policy, error)
        except RetryExhaustedError:
            await self._handle_exhausted(workflow_id, error, current_state.attempt + 1)
            raise

        wf = await self._repo.get_by_id_or_raise(workflow_id)

        await self._events.append_event(
            workflow_id=workflow_id,
            event_type=EVT_RETRY_SCHEDULED,
            payload={
                "attempt": new_state.attempt,
                "next_retry_at": new_state.next_retry_at.isoformat() if new_state.next_retry_at else None,
                "last_error": error,
            },
            actor_type=AuditActorType.system,
            actor_id=None,
            correlation_id=wf.correlation_id,
        )

        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=RETRY_CHANNEL,
                event_type=EVT_RETRY_SCHEDULED,
                payload={
                    "workflow_id": str(workflow_id),
                    "attempt": new_state.attempt,
                    "next_retry_at": new_state.next_retry_at.isoformat() if new_state.next_retry_at else None,
                },
                correlation_id=str(wf.correlation_id),
            ),
        )

        logger.info(
            "retry.scheduled",
            workflow_id=str(workflow_id),
            attempt=new_state.attempt,
        )

        assert new_state.next_retry_at is not None
        return ScheduledRetry(
            workflow_id=workflow_id,
            attempt=new_state.attempt,
            next_retry_at=new_state.next_retry_at,
            last_error=error,
        )

    async def get_due(self, now: datetime | None = None) -> list[ScheduledRetry]:
        """
        Return retries where next_retry_at <= now and workflow still failed.
        Deduplicates: only the latest EVT_RETRY_SCHEDULED per workflow.
        """
        cutoff = now or datetime.now(UTC)

        result = await self._session.execute(
            select(WorkflowEvent)
            .where(WorkflowEvent.event_type == EVT_RETRY_SCHEDULED)
            .order_by(WorkflowEvent.workflow_id, WorkflowEvent.created_at.desc())
        )
        all_events = list(result.scalars().all())

        # Keep only latest per workflow
        seen: set[UUID] = set()
        latest: list[WorkflowEvent] = []
        for evt in all_events:
            if evt.workflow_id not in seen:
                seen.add(evt.workflow_id)
                latest.append(evt)

        due: list[ScheduledRetry] = []
        for evt in latest:
            next_retry_str = evt.payload.get("next_retry_at")
            if not next_retry_str:
                continue
            next_retry_at = datetime.fromisoformat(next_retry_str)
            if next_retry_at > cutoff:
                continue
            wf = await self._repo.get_by_id(evt.workflow_id)
            if wf is None or wf.workflow_status != WorkflowStatus.failed:
                continue
            due.append(
                ScheduledRetry(
                    workflow_id=evt.workflow_id,
                    attempt=evt.payload.get("attempt", 0),
                    next_retry_at=next_retry_at,
                    last_error=evt.payload.get("last_error", ""),
                )
            )

        return due

    async def mark_attempted(self, workflow_id: UUID) -> None:
        """Record that a retry was executed. Audit trail only."""
        wf = await self._repo.get_by_id_or_raise(workflow_id)
        await self._events.append_event(
            workflow_id=workflow_id,
            event_type=EVT_RETRY_ATTEMPTED,
            payload={"attempted_at": datetime.now(UTC).isoformat()},
            actor_type=AuditActorType.system,
            actor_id=None,
            correlation_id=wf.correlation_id,
        )

    async def _get_current_state(self, workflow_id: UUID) -> RetryState:
        """Reconstruct RetryState from most recent retry scheduled event."""
        result = await self._session.execute(
            select(WorkflowEvent)
            .where(
                WorkflowEvent.workflow_id == workflow_id,
                WorkflowEvent.event_type == EVT_RETRY_SCHEDULED,
            )
            .order_by(WorkflowEvent.created_at.desc())
        )
        latest = result.scalars().first()
        if latest is None:
            return RetryState()
        return RetryState(
            attempt=latest.payload.get("attempt", 0),
            last_error=latest.payload.get("last_error", ""),
        )

    async def _handle_exhausted(
        self, workflow_id: UUID, error: str, attempt: int
    ) -> None:
        wf = await self._repo.get_by_id_or_raise(workflow_id)
        await self._events.append_event(
            workflow_id=workflow_id,
            event_type=EVT_RETRY_EXHAUSTED,
            payload={"attempt": attempt, "last_error": error},
            actor_type=AuditActorType.system,
            actor_id=None,
            correlation_id=wf.correlation_id,
        )
        await self._dead_letter.mark(
            workflow_id=workflow_id,
            reason="retry_exhausted",
            retry_count=attempt,
            last_error=error,
        )
