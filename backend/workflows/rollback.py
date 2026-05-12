"""
Workflow rollback foundation.

Rollback = cancel a workflow and record what step it was on.
Append-only: does not delete events. Emits a rollback event.
No compensation side-effects here — callers handle domain cleanup.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import AuditActorType, WorkflowStatus
from models.workflow import Workflow
from workflows.persistence import WorkflowEventRepository, WorkflowRepository

EVT_WORKFLOW_ROLLED_BACK = "workflow.rolled_back"


class RollbackError(Exception):
    pass


class WorkflowRollback:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)
        self._events = WorkflowEventRepository(session)

    async def rollback(
        self,
        workflow_id: UUID,
        reason: str,
        actor_type: AuditActorType = AuditActorType.system,
        actor_id: UUID | None = None,
    ) -> Workflow:
        """
        Cancel a non-terminal workflow and record the step it was on.
        Emits workflow.rolled_back with the last step for audit/replay.
        Raises RollbackError if already terminal.
        """
        workflow = await self._repo.get_by_id_or_raise(workflow_id)

        terminal = {WorkflowStatus.completed, WorkflowStatus.failed, WorkflowStatus.cancelled}
        if workflow.workflow_status in terminal:
            raise RollbackError(
                f"Workflow {workflow_id} is already {workflow.workflow_status} — cannot rollback"
            )

        last_step = workflow.current_step
        workflow.workflow_status = WorkflowStatus.cancelled
        self._session.add(workflow)
        await self._session.flush()

        await self._events.append_event(
            workflow_id=workflow.id,
            event_type=EVT_WORKFLOW_ROLLED_BACK,
            payload={"reason": reason, "rolled_back_from_step": last_step},
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=workflow.correlation_id,
        )

        return workflow
