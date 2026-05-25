"""
AuditTimelineReconstructor — immutable historical event timeline.

Merges workflow_events + domain_events for a workflow into a unified,
time-ordered list of TimelineEntry objects.

Read-only. No DB mutations. Used for forensic analysis and debugging.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.domain_event import DomainEventModel
from workflows.checkpoint import CheckpointRuntime
from workflows.persistence import WorkflowEventRepository, WorkflowRepository

_SUMMARY_MAP: dict[str, str] = {
    "workflow.started": "Workflow started",
    "workflow.advanced": "Step advanced to {step}",
    "workflow.paused": "Workflow paused — {reason}",
    "workflow.resumed": "Workflow resumed",
    "workflow.completed": "Workflow completed",
    "workflow.failed": "Workflow failed — {reason}",
    "workflow.cancelled": "Workflow cancelled — {reason}",
    "workflow.rolled_back": "Workflow rolled back from {rolled_back_from_step}",
    "workflow.rollback.coordinated": "Rollback coordinated (trigger={trigger})",
    "workflow.recovery.checkpoint_restored": "Restored from checkpoint {restored_from_step}",
    "workflow.recovery.resumed": "Recovery: resumed from failed",
    "workflow.approval.requested": "Approval requested ({approval_type})",
    "workflow.approval.resolved": "Approval resolved (approved={approved})",
    "workflow.snapshot.taken": "Snapshot taken (trigger={trigger})",
    "workflow.snapshot.restored": "Snapshot restored",
    "workflow.lease.acquired": "Execution lease acquired by {holder}",
    "workflow.lease.released": "Execution lease released",
    "workflow.lease.expired": "Execution lease expired",
    "workflow.stalled.detected": "Workflow detected as stalled",
    "workflow.orphaned.detected": "Workflow detected as orphaned",
    "workflow.orphaned.recovered": "Orphaned workflow recovered",
    "workflow.dead_letter.recorded": "Dead-lettered ({reason})",
    "workflow.retry.scheduled": "Retry scheduled (attempt {attempt})",
    "workflow.integrity.sweep_completed": "Integrity sweep completed",
}


def _format_summary(event_type: str, payload: dict) -> str:
    template = _SUMMARY_MAP.get(event_type, event_type)
    try:
        return template.format(**payload)
    except (KeyError, ValueError):
        return template


@dataclass(frozen=True)
class TimelineEntry:
    occurred_at: datetime
    event_type: str
    source: str  # "workflow_event" | "domain_event" | "checkpoint"
    actor: str | None
    summary: str
    payload_preview: dict


class AuditTimelineReconstructor:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)
        self._wf_events = WorkflowEventRepository(session)
        self._checkpoints = CheckpointRuntime(session)

    async def build(self, workflow_id: UUID) -> list[TimelineEntry]:
        """
        Build full timeline for workflow_id.
        Merges workflow_events + domain_events ordered by timestamp.
        """
        wf = await self._repo.get_by_id_or_raise(workflow_id)
        entries: list[TimelineEntry] = []

        # Workflow events
        wf_events = await self._wf_events.get_by_workflow(workflow_id)
        for evt in wf_events:
            entries.append(
                TimelineEntry(
                    occurred_at=evt.created_at,
                    event_type=evt.event_type,
                    source="workflow_event",
                    actor=str(evt.actor_id) if evt.actor_id else str(evt.actor_type),
                    summary=_format_summary(evt.event_type, evt.payload),
                    payload_preview=dict(list(evt.payload.items())[:5]),
                )
            )

        # Domain events correlated to this workflow
        result = await self._session.execute(
            select(DomainEventModel).where(
                DomainEventModel.correlation_id == str(wf.correlation_id)
            )
        )
        for dev in result.scalars().all():
            # Avoid duplicating events already in workflow_events
            if dev.event_type.startswith("workflow.") and any(
                e.event_type == dev.event_type
                and abs((e.occurred_at - dev.occurred_at).total_seconds()) < 1
                for e in entries
            ):
                continue
            entries.append(
                TimelineEntry(
                    occurred_at=dev.occurred_at,
                    event_type=dev.event_type,
                    source="domain_event",
                    actor=None,
                    summary=_format_summary(dev.event_type, dev.payload),
                    payload_preview=dict(list(dev.payload.items())[:5]),
                )
            )

        # Checkpoints as timeline markers
        checkpoints = await self._checkpoints.get_all(workflow_id)
        for cp in checkpoints:
            entries.append(
                TimelineEntry(
                    occurred_at=cp.created_at,
                    event_type="checkpoint.set",
                    source="checkpoint",
                    actor=None,
                    summary=f"Checkpoint set at step {cp.step!r}",
                    payload_preview={"step": cp.step, "status": cp.status_at_checkpoint},
                )
            )

        entries.sort(key=lambda e: e.occurred_at)
        return entries

    async def build_since(
        self, workflow_id: UUID, since: datetime
    ) -> list[TimelineEntry]:
        """Return timeline entries after `since`."""
        all_entries = await self.build(workflow_id)
        return [e for e in all_entries if e.occurred_at >= since]
