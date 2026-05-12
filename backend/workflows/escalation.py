"""
Workflow escalation foundation.

Escalation = mark a paused/stalled workflow as escalated and emit an audit event.
No notification dispatch here — callers/workers handle that.
Deterministic: explicit status check, append-only event.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import AuditActorType, WorkflowStatus
from workflows.persistence import WorkflowEventRepository, WorkflowRepository

EVT_WORKFLOW_ESCALATED = "workflow.escalated"

# Statuses eligible for escalation
ESCALATABLE_STATUSES: frozenset[WorkflowStatus] = frozenset({
    WorkflowStatus.active,
    WorkflowStatus.paused,
})


class EscalationError(Exception):
    pass


@dataclass(frozen=True)
class EscalationRecord:
    workflow_id: UUID
    escalated_from_status: WorkflowStatus
    reason: str
    escalated_to: UUID | None  # user to notify — None means system-level


class WorkflowEscalation:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)
        self._events = WorkflowEventRepository(session)

    async def escalate(
        self,
        workflow_id: UUID,
        reason: str,
        escalated_to: UUID | None = None,
        actor_type: AuditActorType = AuditActorType.system,
        actor_id: UUID | None = None,
    ) -> EscalationRecord:
        """
        Record an escalation event on an active or paused workflow.
        Does NOT change workflow_status — escalation is an audit signal.
        Callers decide downstream action (reassign, notify, fail).
        Raises EscalationError if workflow is terminal or pending.
        """
        workflow = await self._repo.get_by_id_or_raise(workflow_id)

        if workflow.workflow_status not in ESCALATABLE_STATUSES:
            raise EscalationError(
                f"Workflow {workflow_id} in status {workflow.workflow_status} is not escalatable"
            )

        record = EscalationRecord(
            workflow_id=workflow_id,
            escalated_from_status=workflow.workflow_status,
            reason=reason,
            escalated_to=escalated_to,
        )

        await self._events.append_event(
            workflow_id=workflow.id,
            event_type=EVT_WORKFLOW_ESCALATED,
            payload={
                "reason": reason,
                "escalated_to": str(escalated_to) if escalated_to else None,
                "from_status": workflow.workflow_status,
            },
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=workflow.correlation_id,
        )

        return record
