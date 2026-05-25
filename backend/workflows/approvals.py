"""
Workflow approval gate.

Handles: request approval, resolve (approve/reject), check blocking state.
Pauses workflow when approval is requested. Resumes on approval.
Fails/cancels workflow on rejection (caller decides).
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.approval import Approval
from models.enums import (
    ApprovalStatus,
    ApprovalType,
    AuditActorType,
    RiskLevel,
    WorkflowStatus,
)
from repositories.approval import ApprovalRepository
from workflows.persistence import WorkflowEventRepository, WorkflowRepository
from workflows.transitions import TransitionError

EVT_APPROVAL_REQUESTED = "workflow.approval.requested"
EVT_APPROVAL_RESOLVED = "workflow.approval.resolved"

# Statuses that can be resolved (approved/rejected)
_RESOLVABLE_STATUSES: frozenset[ApprovalStatus] = frozenset({
    ApprovalStatus.pending,
    ApprovalStatus.escalated,
})


class ApprovalGateError(Exception):
    """Raised when approval gate constraints are violated."""


class WorkflowApprovalGate:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._workflows = WorkflowRepository(session)
        self._approvals = ApprovalRepository(session)
        self._events = WorkflowEventRepository(session)

    async def request_approval(
        self,
        workflow_id: UUID,
        approval_type: ApprovalType,
        requested_by: UUID | None = None,
        risk_level: RiskLevel = RiskLevel.low,
        expires_at: datetime | None = None,
    ) -> Approval:
        """
        Create a pending approval and pause the workflow.
        Raises if workflow is not active.
        """
        workflow = await self._workflows.get_for_update_or_raise(workflow_id)

        if workflow.workflow_status != WorkflowStatus.active:
            raise TransitionError(
                workflow_id,
                workflow.workflow_status,
                WorkflowStatus.paused,
                reason="workflow must be active to request approval",
            )

        # Check no existing pending approval of same type
        existing = await self._approvals.get_by_workflow(workflow_id)
        for appr in existing:
            if appr.approval_type == approval_type and appr.approval_status == ApprovalStatus.pending:
                raise ApprovalGateError(
                    f"Workflow {workflow_id} already has pending {approval_type} approval"
                )

        approval = await self._approvals.create(
            workflow_id=workflow_id,
            approval_type=approval_type,
            approval_status=ApprovalStatus.pending,
            requested_by=requested_by,
            risk_level=risk_level,
            expires_at=expires_at,
        )

        # Pause workflow
        workflow.workflow_status = WorkflowStatus.paused
        self._session.add(workflow)
        await self._session.flush()

        await self._events.append_event(
            workflow_id=workflow_id,
            event_type=EVT_APPROVAL_REQUESTED,
            payload={
                "approval_id": str(approval.id),
                "approval_type": approval_type,
                "risk_level": risk_level,
            },
            actor_type=AuditActorType.user,
            actor_id=requested_by,
            correlation_id=workflow.correlation_id,
        )

        return approval

    async def resolve(
        self,
        approval_id: UUID,
        resolved_by: UUID,
        approved: bool,
        notes: str = "",
    ) -> Approval:
        """
        Approve or reject a pending approval.
        On approval: resumes workflow.
        On rejection: fails workflow.
        """
        approval = await self._approvals.get_by_id_or_raise(approval_id)

        if approval.approval_status not in _RESOLVABLE_STATUSES:
            raise ApprovalGateError(
                f"Approval {approval_id} is {approval.approval_status} — not resolvable"
            )

        new_status = ApprovalStatus.approved if approved else ApprovalStatus.rejected
        approval.approval_status = new_status
        approval.resolved_by = resolved_by
        approval.resolution_notes = notes
        self._session.add(approval)
        await self._session.flush()

        workflow = await self._workflows.get_by_id_or_raise(approval.workflow_id)

        if approved:
            workflow.workflow_status = WorkflowStatus.active
        else:
            workflow.workflow_status = WorkflowStatus.failed

        self._session.add(workflow)
        await self._session.flush()

        await self._events.append_event(
            workflow_id=workflow.id,
            event_type=EVT_APPROVAL_RESOLVED,
            payload={
                "approval_id": str(approval_id),
                "approval_type": approval.approval_type,
                "approved": approved,
                "notes": notes,
            },
            actor_type=AuditActorType.user,
            actor_id=resolved_by,
            correlation_id=workflow.correlation_id,
        )

        return approval

    async def has_pending_approval(self, workflow_id: UUID) -> bool:
        """Return True if any approval is currently pending for this workflow."""
        existing = await self._approvals.get_by_workflow(workflow_id)
        return any(a.approval_status == ApprovalStatus.pending for a in existing)
