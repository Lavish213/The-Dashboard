"""
SnapshotRuntime — full workflow state capture and restoration.

take()    — serialize complete workflow state to a snapshot row
restore() — restore workflow status/step from a snapshot (non-destructive)

Snapshot state includes: workflow fields, pending approvals summary,
latest checkpoint, active lease presence. Immutable after write.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from events.contracts import DomainEvent
from events.emitter import event_emitter
from models.enums import AuditActorType, WorkflowStatus
from models.workflow_snapshot import WorkflowSnapshot
from repositories.approval import ApprovalRepository
from workflows.checkpoint import CheckpointRuntime
from workflows.lease import LeaseRuntime
from workflows.persistence import WorkflowEventRepository, WorkflowRepository

logger = structlog.get_logger(__name__)

SNAPSHOT_CHANNEL = "workflows"
EVT_SNAPSHOT_TAKEN = "workflow.snapshot.taken"
EVT_SNAPSHOT_RESTORED = "workflow.snapshot.restored"


@dataclass(frozen=True)
class SnapshotResult:
    snapshot_id: UUID
    workflow_id: UUID
    workflow_status: str
    current_step: str | None
    captured_at: datetime
    trigger: str | None


class SnapshotRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)
        self._events = WorkflowEventRepository(session)
        self._checkpoints = CheckpointRuntime(session)
        self._approvals = ApprovalRepository(session)
        self._lease = LeaseRuntime(session)

    async def take(
        self,
        workflow_id: UUID,
        trigger: str | None = None,
    ) -> SnapshotResult:
        """
        Capture full workflow state snapshot.
        Includes workflow fields, pending approvals, latest checkpoint, lease presence.
        """
        wf = await self._repo.get_by_id_or_raise(workflow_id)
        checkpoint = await self._checkpoints.get_latest(workflow_id)
        approvals = await self._approvals.get_by_workflow(workflow_id)
        active_lease = await self._lease.get_active(workflow_id)

        pending_approvals = [
            {
                "approval_id": str(a.id),
                "approval_type": str(a.approval_type),
                "approval_status": str(a.approval_status),
            }
            for a in approvals
            if str(a.approval_status) in ("pending", "escalated")
        ]

        state = {
            "workflow_id": str(workflow_id),
            "workflow_type": str(wf.workflow_type),
            "workflow_status": str(wf.workflow_status),
            "current_step": wf.current_step,
            "correlation_id": str(wf.correlation_id),
            "lead_id": str(wf.lead_id) if wf.lead_id else None,
            "initiated_by": str(wf.initiated_by) if wf.initiated_by else None,
            "pending_approvals": pending_approvals,
            "latest_checkpoint": {
                "step": checkpoint.step,
                "status": checkpoint.status_at_checkpoint,
                "payload": checkpoint.payload,
            } if checkpoint else None,
            "active_lease": {
                "holder": active_lease.holder,
                "expires_at": active_lease.expires_at.isoformat(),
            } if active_lease else None,
        }

        snap = WorkflowSnapshot(
            workflow_id=workflow_id,
            workflow_status=str(wf.workflow_status),
            current_step=wf.current_step,
            state=state,
            trigger=trigger,
        )
        self._session.add(snap)
        await self._session.flush()

        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=SNAPSHOT_CHANNEL,
                event_type=EVT_SNAPSHOT_TAKEN,
                payload={
                    "workflow_id": str(workflow_id),
                    "snapshot_id": str(snap.id),
                    "workflow_status": str(wf.workflow_status),
                    "trigger": trigger,
                },
                correlation_id=str(wf.correlation_id),
            ),
        )

        logger.info(
            "snapshot.taken",
            workflow_id=str(workflow_id),
            snapshot_id=str(snap.id),
            trigger=trigger,
        )

        return SnapshotResult(
            snapshot_id=snap.id,
            workflow_id=workflow_id,
            workflow_status=str(wf.workflow_status),
            current_step=wf.current_step,
            captured_at=snap.captured_at,
            trigger=trigger,
        )

    async def restore(
        self,
        snapshot_id: UUID,
        actor_id: UUID | None = None,
    ) -> SnapshotResult:
        """
        Restore workflow status and step from snapshot.
        Non-destructive: appends recovery event, does not delete other events.
        Only valid for non-terminal workflows.
        """
        result = await self._session.execute(
            select(WorkflowSnapshot).where(WorkflowSnapshot.id == snapshot_id)
        )
        snap = result.scalar_one_or_none()
        if snap is None:
            raise ValueError(f"Snapshot {snapshot_id} not found")

        wf = await self._repo.get_for_update_or_raise(snap.workflow_id)
        terminal = {WorkflowStatus.completed, WorkflowStatus.cancelled}
        if wf.workflow_status in terminal:
            raise ValueError(
                f"Cannot restore snapshot: workflow is terminal ({wf.workflow_status})"
            )

        snap_status = WorkflowStatus(snap.workflow_status)
        wf.workflow_status = snap_status
        wf.current_step = snap.current_step
        self._session.add(wf)
        await self._session.flush()

        await self._events.append_event(
            workflow_id=wf.id,
            event_type="workflow.snapshot.restored",
            payload={
                "snapshot_id": str(snapshot_id),
                "restored_status": snap.workflow_status,
                "restored_step": snap.current_step,
            },
            actor_type=AuditActorType.system,
            actor_id=actor_id,
            correlation_id=wf.correlation_id,
        )

        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=SNAPSHOT_CHANNEL,
                event_type=EVT_SNAPSHOT_RESTORED,
                payload={
                    "workflow_id": str(wf.id),
                    "snapshot_id": str(snapshot_id),
                    "restored_status": snap.workflow_status,
                },
                correlation_id=str(wf.correlation_id),
            ),
        )

        logger.info(
            "snapshot.restored",
            workflow_id=str(wf.id),
            snapshot_id=str(snapshot_id),
        )

        return SnapshotResult(
            snapshot_id=snap.id,
            workflow_id=wf.id,
            workflow_status=snap.workflow_status,
            current_step=snap.current_step,
            captured_at=snap.captured_at,
            trigger=snap.trigger,
        )

    async def get_latest(self, workflow_id: UUID) -> SnapshotResult | None:
        """Return most recent snapshot for workflow, or None."""
        result = await self._session.execute(
            select(WorkflowSnapshot)
            .where(WorkflowSnapshot.workflow_id == workflow_id)
            .order_by(WorkflowSnapshot.captured_at.desc())
            .limit(1)
        )
        snap = result.scalar_one_or_none()
        if snap is None:
            return None
        return SnapshotResult(
            snapshot_id=snap.id,
            workflow_id=workflow_id,
            workflow_status=snap.workflow_status,
            current_step=snap.current_step,
            captured_at=snap.captured_at,
            trigger=snap.trigger,
        )

    async def get_all(self, workflow_id: UUID) -> list[SnapshotResult]:
        """Return all snapshots ordered by capture time (oldest first)."""
        result = await self._session.execute(
            select(WorkflowSnapshot)
            .where(WorkflowSnapshot.workflow_id == workflow_id)
            .order_by(WorkflowSnapshot.captured_at.asc())
        )
        return [
            SnapshotResult(
                snapshot_id=s.id,
                workflow_id=workflow_id,
                workflow_status=s.workflow_status,
                current_step=s.current_step,
                captured_at=s.captured_at,
                trigger=s.trigger,
            )
            for s in result.scalars().all()
        ]
