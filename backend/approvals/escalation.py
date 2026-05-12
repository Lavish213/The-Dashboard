"""
ApprovalEscalationRuntime: escalation state and events for approvals.

Escalation = audit signal only. Does NOT dispatch notifications.
Replay-safe: escalation events are append-only.
Status transitions: pending -> escalated (audit mark, not terminal).
"""

from dataclasses import dataclass
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import ApprovalStatus, AuditActorType
from realtime.broadcast import broadcast_service
from realtime.protocol import RealtimeEvent
from repositories.approval import ApprovalRepository
from workflows.persistence import WorkflowEventRepository

logger = structlog.get_logger(__name__)

APPROVAL_CHANNEL = "approvals"
EVT_APPROVAL_ESCALATED = "approval.escalated"

# Statuses eligible for escalation
ESCALATABLE_STATUSES: frozenset[ApprovalStatus] = frozenset({ApprovalStatus.pending})


class EscalationError(Exception):
    pass


@dataclass(frozen=True)
class ApprovalEscalationRecord:
    approval_id: UUID
    workflow_id: UUID
    reason: str
    escalated_to: UUID | None


class ApprovalEscalationRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ApprovalRepository(session)
        self._events = WorkflowEventRepository(session)

    async def escalate(
        self,
        approval_id: UUID,
        reason: str,
        escalated_to: UUID | None = None,
        actor_id: UUID | None = None,
    ) -> ApprovalEscalationRecord:
        """
        Mark a pending approval as escalated and emit an audit event.
        Does NOT resolve the approval — escalated approvals still require resolution.
        Raises EscalationError if approval is not in an escalatable status.
        """
        approval = await self._repo.get_for_update_or_raise(approval_id)

        if approval.approval_status not in ESCALATABLE_STATUSES:
            raise EscalationError(
                f"Approval {approval_id} is {approval.approval_status}, not escalatable"
            )

        approval.approval_status = ApprovalStatus.escalated
        self._session.add(approval)
        await self._session.flush()

        await self._events.append_event(
            workflow_id=approval.workflow_id,
            event_type=EVT_APPROVAL_ESCALATED,
            payload={
                "approval_id": str(approval_id),
                "approval_type": approval.approval_type,
                "reason": reason,
                "escalated_to": str(escalated_to) if escalated_to else None,
            },
            actor_type=AuditActorType.system,
            actor_id=actor_id,
            correlation_id=approval.workflow_id,
        )

        await broadcast_service.publish(RealtimeEvent(
            channel=APPROVAL_CHANNEL,
            event_type=EVT_APPROVAL_ESCALATED,
            payload={
                "approval_id": str(approval_id),
                "workflow_id": str(approval.workflow_id),
                "approval_type": approval.approval_type,
                "reason": reason,
                "escalated_to": str(escalated_to) if escalated_to else None,
            },
            correlation_id=str(approval.workflow_id),
        ))

        logger.info(
            "approval.escalated",
            approval_id=str(approval_id),
            workflow_id=str(approval.workflow_id),
            reason=reason,
        )

        return ApprovalEscalationRecord(
            approval_id=approval_id,
            workflow_id=approval.workflow_id,
            reason=reason,
            escalated_to=escalated_to,
        )
