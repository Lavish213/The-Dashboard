"""
DeadLetterRuntime — record permanently failed workflows.

Dead-letter is append-only: stored as workflow_event + domain_event.
Does not change workflow status (caller must ensure workflow is failed).
A workflow is dead-lettered if it has a workflow.dead_letter.recorded event.
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
from models.enums import AuditActorType
from models.workflow_event import WorkflowEvent
from workflows.persistence import WorkflowEventRepository, WorkflowRepository

logger = structlog.get_logger(__name__)

DEAD_LETTER_CHANNEL = "workflows"
EVT_DEAD_LETTER = "workflow.dead_letter.recorded"


@dataclass(frozen=True)
class DeadLetterRecord:
    workflow_id: UUID
    reason: str
    retry_count: int
    last_error: str
    recorded_at: datetime


class DeadLetterRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)
        self._events = WorkflowEventRepository(session)

    async def mark(
        self,
        workflow_id: UUID,
        reason: str,
        retry_count: int = 0,
        last_error: str = "",
    ) -> DeadLetterRecord:
        """
        Record workflow as dead-lettered.
        Appends to workflow_events and emits domain event to workflows channel.
        """
        wf = await self._repo.get_by_id_or_raise(workflow_id)
        now = datetime.now(UTC)

        await self._events.append_event(
            workflow_id=workflow_id,
            event_type=EVT_DEAD_LETTER,
            payload={
                "reason": reason,
                "retry_count": retry_count,
                "last_error": last_error,
                "recorded_at": now.isoformat(),
            },
            actor_type=AuditActorType.system,
            actor_id=None,
            correlation_id=wf.correlation_id,
        )

        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=DEAD_LETTER_CHANNEL,
                event_type=EVT_DEAD_LETTER,
                payload={
                    "workflow_id": str(workflow_id),
                    "reason": reason,
                    "retry_count": retry_count,
                },
                correlation_id=str(wf.correlation_id),
            ),
        )

        logger.info(
            "dead_letter.recorded",
            workflow_id=str(workflow_id),
            reason=reason,
            retries=retry_count,
        )

        return DeadLetterRecord(
            workflow_id=workflow_id,
            reason=reason,
            retry_count=retry_count,
            last_error=last_error,
            recorded_at=now,
        )

    async def get_dead_letters(self) -> list[DeadLetterRecord]:
        """Return all dead-letter records ordered by most recent first."""
        result = await self._session.execute(
            select(WorkflowEvent)
            .where(WorkflowEvent.event_type == EVT_DEAD_LETTER)
            .order_by(WorkflowEvent.created_at.desc())
        )
        return [
            DeadLetterRecord(
                workflow_id=e.workflow_id,
                reason=e.payload.get("reason", ""),
                retry_count=e.payload.get("retry_count", 0),
                last_error=e.payload.get("last_error", ""),
                recorded_at=e.created_at,
            )
            for e in result.scalars().all()
        ]
