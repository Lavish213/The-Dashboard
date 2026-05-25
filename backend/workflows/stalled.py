"""
StalledDetector — find workflows that have stopped progressing.

A workflow is stalled when it is active/paused but has had no new events
for longer than max_idle_seconds. Detection is read-only.

mark_stalled() emits a domain event — advisory only, does not transition.
Caller decides recovery action (retry, orphaned recovery, operator alert).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from events.contracts import DomainEvent
from events.emitter import event_emitter
from models.enums import WorkflowStatus
from models.workflow import Workflow
from models.workflow_event import WorkflowEvent

logger = structlog.get_logger(__name__)

STALL_CHANNEL = "workflows"
EVT_STALLED = "workflow.stalled.detected"

DEFAULT_MAX_IDLE_SECONDS = 3600  # 1 hour


@dataclass(frozen=True)
class StalledWorkflow:
    workflow_id: UUID
    current_status: WorkflowStatus
    last_event_at: datetime
    stalled_for_seconds: float


class StalledDetector:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_stalled(
        self,
        max_idle_seconds: int = DEFAULT_MAX_IDLE_SECONDS,
        now: datetime | None = None,
    ) -> list[StalledWorkflow]:
        """
        Find active/paused workflows whose last event is older than max_idle_seconds.
        Every workflow has at least one event (workflow.started), so INNER JOIN is safe.
        """
        now_ts = now or datetime.now(UTC)
        cutoff = now_ts - timedelta(seconds=max_idle_seconds)

        latest_evt = (
            select(
                WorkflowEvent.workflow_id,
                func.max(WorkflowEvent.created_at).label("last_event_at"),
            )
            .group_by(WorkflowEvent.workflow_id)
            .subquery()
        )

        result = await self._session.execute(
            select(Workflow, latest_evt.c.last_event_at)
            .join(latest_evt, Workflow.id == latest_evt.c.workflow_id)
            .where(
                Workflow.workflow_status.in_([WorkflowStatus.active, WorkflowStatus.paused]),
                latest_evt.c.last_event_at < cutoff,
            )
        )

        stalled: list[StalledWorkflow] = []
        for wf, last_event_at in result.all():
            stalled_for = (now_ts - last_event_at).total_seconds()
            stalled.append(
                StalledWorkflow(
                    workflow_id=wf.id,
                    current_status=wf.workflow_status,
                    last_event_at=last_event_at,
                    stalled_for_seconds=stalled_for,
                )
            )

        return stalled

    async def mark_stalled(
        self,
        workflow_id: UUID,
        stalled_for_seconds: float,
    ) -> None:
        """Emit domain event for stalled workflow. Read-only on workflow state."""
        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=STALL_CHANNEL,
                event_type=EVT_STALLED,
                payload={
                    "workflow_id": str(workflow_id),
                    "stalled_for_seconds": stalled_for_seconds,
                },
            ),
        )
        logger.info(
            "workflow.stalled",
            workflow_id=str(workflow_id),
            stalled_for_seconds=stalled_for_seconds,
        )
