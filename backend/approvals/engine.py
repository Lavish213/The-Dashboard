"""
ApprovalEngine: operational governance wrapper around WorkflowApprovalGate.

Responsibilities:
- request approval (delegates to gate)
- resolve approval (delegates to gate)
- emit realtime broadcast events after each mutation
- NO intelligence, NO policy evaluation

WorkflowApprovalGate remains the deterministic core.
This layer adds observability and realtime fan-out only.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.approval import Approval
from models.enums import ApprovalType, RiskLevel
from realtime.broadcast import broadcast_service
from realtime.protocol import RealtimeEvent
from workflows.approvals import WorkflowApprovalGate

APPROVAL_CHANNEL = "approvals"
EVT_APPROVAL_REQUESTED = "approval.requested"
EVT_APPROVAL_RESOLVED = "approval.resolved"


class ApprovalEngineError(Exception):
    """Raised for engine-level constraint violations."""


class ApprovalEngine:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._gate = WorkflowApprovalGate(session)

    async def request(
        self,
        workflow_id: UUID,
        approval_type: ApprovalType,
        requested_by: UUID | None = None,
        risk_level: RiskLevel = RiskLevel.low,
        expires_at: datetime | None = None,
    ) -> Approval:
        """
        Request an approval via the workflow gate.
        Pauses the workflow. Emits realtime event.
        Raises ApprovalGateError / TransitionError on constraint violation.
        """
        approval = await self._gate.request_approval(
            workflow_id=workflow_id,
            approval_type=approval_type,
            requested_by=requested_by,
            risk_level=risk_level,
            expires_at=expires_at,
        )

        await broadcast_service.publish(RealtimeEvent(
            channel=APPROVAL_CHANNEL,
            event_type=EVT_APPROVAL_REQUESTED,
            payload={
                "approval_id": str(approval.id),
                "workflow_id": str(workflow_id),
                "approval_type": approval_type,
                "risk_level": risk_level,
                "expires_at": expires_at.isoformat() if expires_at else None,
            },
            correlation_id=str(workflow_id),
        ))

        return approval

    async def resolve(
        self,
        approval_id: UUID,
        resolved_by: UUID,
        approved: bool,
        notes: str = "",
    ) -> Approval:
        """
        Approve or reject a pending approval via the workflow gate.
        Resumes workflow on approval; fails on rejection.
        Emits realtime event.
        Raises ApprovalGateError if already resolved.
        """
        approval = await self._gate.resolve(
            approval_id=approval_id,
            resolved_by=resolved_by,
            approved=approved,
            notes=notes,
        )

        await broadcast_service.publish(RealtimeEvent(
            channel=APPROVAL_CHANNEL,
            event_type=EVT_APPROVAL_RESOLVED,
            payload={
                "approval_id": str(approval_id),
                "workflow_id": str(approval.workflow_id),
                "approval_type": approval.approval_type,
                "approved": approved,
                "resolved_by": str(resolved_by),
                "notes": notes,
            },
            correlation_id=str(approval.workflow_id),
        ))

        return approval

    async def has_pending(self, workflow_id: UUID) -> bool:
        """Return True if any approval is currently pending for this workflow."""
        return await self._gate.has_pending_approval(workflow_id)
