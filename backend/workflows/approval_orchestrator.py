"""
ApprovalPauseOrchestrator — full approval lifecycle coordination.

Orchestrates the pause → approve/reject → resume/rollback lifecycle.
Higher-level than WorkflowApprovalGate: handles snapshot, rollback, events.

resume_on_approval:  resolve approved → workflow resumes active
rollback_on_rejection: mark rejected → RollbackCoordinator cancels workflow

Callers use this instead of calling gate + runtime + coordinator separately.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from events.contracts import DomainEvent
from events.emitter import event_emitter
from models.enums import ApprovalStatus, ApprovalType, RiskLevel
from repositories.approval import ApprovalRepository
from workflows.approvals import WorkflowApprovalGate
from workflows.coordinator import RollbackCoordinator
from workflows.persistence import WorkflowRepository
from workflows.snapshot import SnapshotRuntime

logger = structlog.get_logger(__name__)

ORCH_CHANNEL = "workflows"
EVT_APPROVAL_LIFECYCLE_PAUSED = "workflow.approval_lifecycle.paused"
EVT_APPROVAL_LIFECYCLE_RESUMED = "workflow.approval_lifecycle.resumed"
EVT_APPROVAL_LIFECYCLE_REJECTED = "workflow.approval_lifecycle.rejected"


@dataclass(frozen=True)
class ApprovalLifecycleResult:
    workflow_id: UUID
    approval_id: UUID
    outcome: str  # "paused" | "resumed" | "rejected"
    snapshot_id: UUID | None = None


class ApprovalPauseOrchestrator:
    """
    Lifecycle coordinator for approval-paused workflows.

    pause_for_approval  → pause workflow + create approval + take snapshot
    resume_on_approval  → approve + resume workflow + emit lifecycle event
    rollback_on_rejection → reject approval + cancel workflow via RollbackCoordinator
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._gate = WorkflowApprovalGate(session)
        self._repo = WorkflowRepository(session)
        self._approvals = ApprovalRepository(session)
        self._rollback = RollbackCoordinator(session)
        self._snapshots = SnapshotRuntime(session)

    async def pause_for_approval(
        self,
        workflow_id: UUID,
        approval_type: ApprovalType,
        requested_by: UUID | None = None,
        risk_level: RiskLevel = RiskLevel.low,
        expires_at: datetime | None = None,
        take_snapshot: bool = True,
    ) -> ApprovalLifecycleResult:
        """
        Pause workflow and create approval request.
        Optionally takes a snapshot before pausing (for restore if rejected).
        """
        snap_id: UUID | None = None
        if take_snapshot:
            snap = await self._snapshots.take(workflow_id, trigger="approval_requested")
            snap_id = snap.snapshot_id

        approval = await self._gate.request_approval(
            workflow_id=workflow_id,
            approval_type=approval_type,
            requested_by=requested_by,
            risk_level=risk_level,
            expires_at=expires_at,
        )

        wf = await self._repo.get_by_id_or_raise(workflow_id)
        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=ORCH_CHANNEL,
                event_type=EVT_APPROVAL_LIFECYCLE_PAUSED,
                payload={
                    "workflow_id": str(workflow_id),
                    "approval_id": str(approval.id),
                    "approval_type": str(approval_type),
                    "snapshot_id": str(snap_id) if snap_id else None,
                },
                correlation_id=str(wf.correlation_id),
            ),
        )

        logger.info(
            "approval_lifecycle.paused",
            workflow_id=str(workflow_id),
            approval_id=str(approval.id),
        )

        return ApprovalLifecycleResult(
            workflow_id=workflow_id,
            approval_id=approval.id,
            outcome="paused",
            snapshot_id=snap_id,
        )

    async def resume_on_approval(
        self,
        approval_id: UUID,
        resolved_by: UUID,
        notes: str = "",
    ) -> ApprovalLifecycleResult:
        """
        Approve and resume workflow. Delegates resolution to gate.
        """
        approval = await self._approvals.get_by_id_or_raise(approval_id)
        workflow_id = approval.workflow_id

        await self._gate.resolve(
            approval_id=approval_id,
            resolved_by=resolved_by,
            approved=True,
            notes=notes,
        )

        wf = await self._repo.get_by_id_or_raise(workflow_id)
        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=ORCH_CHANNEL,
                event_type=EVT_APPROVAL_LIFECYCLE_RESUMED,
                payload={
                    "workflow_id": str(workflow_id),
                    "approval_id": str(approval_id),
                    "resolved_by": str(resolved_by),
                },
                correlation_id=str(wf.correlation_id),
            ),
        )

        logger.info(
            "approval_lifecycle.resumed",
            workflow_id=str(workflow_id),
            approval_id=str(approval_id),
        )

        return ApprovalLifecycleResult(
            workflow_id=workflow_id,
            approval_id=approval_id,
            outcome="resumed",
        )

    async def rollback_on_rejection(
        self,
        approval_id: UUID,
        workflow_id: UUID,
        resolved_by: UUID | None = None,
        reason: str = "approval_rejected",
    ) -> ApprovalLifecycleResult:
        """
        Reject approval and cancel workflow via RollbackCoordinator.
        Marks approval rejected directly, then coordinates rollback.
        Workflow ends as cancelled (not failed) — rejection is governance, not system error.
        """
        # Mark approval rejected without triggering gate's workflow fail
        approval = await self._approvals.get_for_update_or_raise(approval_id)
        approval.approval_status = ApprovalStatus.rejected
        if resolved_by:
            approval.resolved_by = resolved_by
        approval.resolution_notes = reason
        self._session.add(approval)
        await self._session.flush()

        # Cancel workflow via coordinator (records compensating action + domain event)
        await self._rollback.rollback_on_approval_rejection(
            approval_id=approval_id,
            workflow_id=workflow_id,
            rejected_by=resolved_by,
            reason=reason,
        )

        wf = await self._repo.get_by_id_or_raise(workflow_id)
        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=ORCH_CHANNEL,
                event_type=EVT_APPROVAL_LIFECYCLE_REJECTED,
                payload={
                    "workflow_id": str(workflow_id),
                    "approval_id": str(approval_id),
                    "resolved_by": str(resolved_by) if resolved_by else None,
                    "reason": reason,
                },
                correlation_id=str(wf.correlation_id),
            ),
        )

        logger.info(
            "approval_lifecycle.rejected",
            workflow_id=str(workflow_id),
            approval_id=str(approval_id),
        )

        return ApprovalLifecycleResult(
            workflow_id=workflow_id,
            approval_id=approval_id,
            outcome="rejected",
        )
