"""
RuntimeObservability + GovernanceMetrics — structured hooks and metrics.

ObservabilityRuntime: emit structured domain events for key runtime transitions.
GovernanceMetrics: read-only queries to compute governance KPIs from event log.

All operations are idempotent and replay-safe.
No external metric stores — emits to domain_events channel for downstream consumers.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from events.contracts import DomainEvent
from events.emitter import event_emitter
from models.enums import WorkflowStatus
from repositories.approval import ApprovalRepository
from workflows.checkpoint import CheckpointRuntime
from workflows.persistence import WorkflowEventRepository, WorkflowRepository

logger = structlog.get_logger(__name__)

OBS_CHANNEL = "workflows.observability"
EVT_METRIC = "workflow.metric.recorded"

# Event types counted as rollbacks
_ROLLBACK_EVENTS = frozenset({
    "workflow.rolled_back",
    "workflow.rollback.coordinated",
})


class ObservabilityRuntime:
    """
    Emit structured observability events for runtime transitions.
    These are advisory — callers invoke after key operations for metric fanout.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        workflow_id: UUID,
        metric_name: str,
        value: float,
        tags: dict | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a structured metric domain event."""
        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=OBS_CHANNEL,
                event_type=EVT_METRIC,
                payload={
                    "workflow_id": str(workflow_id),
                    "metric": metric_name,
                    "value": value,
                    "tags": tags or {},
                },
                correlation_id=correlation_id,
            ),
        )
        logger.debug(
            "observability.metric",
            workflow_id=str(workflow_id),
            metric=metric_name,
            value=value,
        )

    async def on_transition(
        self,
        workflow_id: UUID,
        from_status: WorkflowStatus,
        to_status: WorkflowStatus,
        duration_seconds: float | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Emit transition hook event for observability consumers."""
        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=OBS_CHANNEL,
                event_type="workflow.transition.observed",
                payload={
                    "workflow_id": str(workflow_id),
                    "from_status": str(from_status),
                    "to_status": str(to_status),
                    "duration_seconds": duration_seconds,
                },
                correlation_id=correlation_id,
            ),
        )


# ---------------------------------------------------------------------------
# GovernanceMetrics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkflowMetrics:
    workflow_id: UUID
    total_events: int
    retry_count: int
    rollback_count: int
    checkpoint_count: int
    event_type_counts: dict[str, int]


@dataclass(frozen=True)
class ApprovalCycleMetrics:
    workflow_id: UUID
    total_approvals: int
    resolved_count: int
    pending_count: int
    avg_cycle_seconds: float | None  # None if no resolved approvals with timestamps


class GovernanceMetrics:
    """
    Read-only governance KPI computations from event log and approval records.
    No DB mutations.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)
        self._events = WorkflowEventRepository(session)
        self._checkpoints = CheckpointRuntime(session)
        self._approvals = ApprovalRepository(session)

    async def workflow_metrics(self, workflow_id: UUID) -> WorkflowMetrics:
        """Compute event-based metrics for a single workflow."""
        await self._repo.get_by_id_or_raise(workflow_id)  # 404 guard
        events = await self._events.get_by_workflow(workflow_id)

        type_counts: dict[str, int] = {}
        for evt in events:
            type_counts[evt.event_type] = type_counts.get(evt.event_type, 0) + 1

        retry_count = type_counts.get("workflow.retry.scheduled", 0)
        rollback_count = sum(
            type_counts.get(et, 0) for et in _ROLLBACK_EVENTS
        )
        checkpoints = await self._checkpoints.get_all(workflow_id)

        return WorkflowMetrics(
            workflow_id=workflow_id,
            total_events=len(events),
            retry_count=retry_count,
            rollback_count=rollback_count,
            checkpoint_count=len(checkpoints),
            event_type_counts=type_counts,
        )

    async def approval_metrics(self, workflow_id: UUID) -> ApprovalCycleMetrics:
        """Compute approval lifecycle metrics for a workflow."""
        await self._repo.get_by_id_or_raise(workflow_id)
        all_approvals = await self._approvals.get_by_workflow(workflow_id)

        from models.enums import ApprovalStatus

        resolved = [
            a for a in all_approvals
            if a.approval_status in (ApprovalStatus.approved, ApprovalStatus.rejected)
        ]
        pending = [
            a for a in all_approvals
            if a.approval_status in (ApprovalStatus.pending, ApprovalStatus.escalated)
        ]

        # Cycle time: created_at → updated_at for resolved approvals
        cycle_times: list[float] = []
        for a in resolved:
            if a.created_at and a.updated_at and a.updated_at > a.created_at:
                cycle_times.append((a.updated_at - a.created_at).total_seconds())

        avg_cycle = sum(cycle_times) / len(cycle_times) if cycle_times else None

        return ApprovalCycleMetrics(
            workflow_id=workflow_id,
            total_approvals=len(all_approvals),
            resolved_count=len(resolved),
            pending_count=len(pending),
            avg_cycle_seconds=avg_cycle,
        )
