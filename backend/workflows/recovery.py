"""
Workflow recovery: resume failed/paused workflows and replay event history.

Recovery is deterministic: given the same event log, same state is produced.
No side effects beyond DB reads.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import AuditActorType, WorkflowStatus
from models.workflow import Workflow
from models.workflow_event import WorkflowEvent
from workflows.persistence import WorkflowEventRepository, WorkflowRepository
from workflows.transitions import TransitionError

# Event types that are state-changing (used during replay)
_STATUS_EVENTS: dict[str, WorkflowStatus] = {
    "workflow.started": WorkflowStatus.active,
    "workflow.paused": WorkflowStatus.paused,
    "workflow.resumed": WorkflowStatus.active,
    "workflow.completed": WorkflowStatus.completed,
    "workflow.failed": WorkflowStatus.failed,
    "workflow.cancelled": WorkflowStatus.cancelled,
}


@dataclass(frozen=True)
class ReplayResult:
    workflow_id: UUID
    replayed_events: int
    final_status: WorkflowStatus
    final_step: str | None


class WorkflowRecovery:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)
        self._events = WorkflowEventRepository(session)

    async def resume_failed(
        self,
        workflow_id: UUID,
        actor_id: UUID | None = None,
    ) -> Workflow:
        """
        Transition a failed workflow back to active for retry.
        Caller is responsible for re-advancing to the correct step.
        """
        workflow = await self._repo.get_by_id_or_raise(workflow_id)

        if workflow.workflow_status != WorkflowStatus.failed:
            raise TransitionError(
                workflow_id,
                workflow.workflow_status,
                WorkflowStatus.active,
                reason="resume_failed only applies to failed workflows",
            )

        # failed -> active is not in normal transitions; recovery is explicit
        workflow.workflow_status = WorkflowStatus.active
        self._session.add(workflow)
        await self._session.flush()

        await self._events.append_event(
            workflow_id=workflow.id,
            event_type="workflow.recovery.resumed",
            payload={"from_status": WorkflowStatus.failed},
            actor_type=AuditActorType.system,
            actor_id=actor_id,
            correlation_id=workflow.correlation_id,
        )

        return workflow

    async def replay(self, workflow_id: UUID) -> ReplayResult:
        """
        Replay event log to derive current state.
        Does NOT mutate DB — read-only consistency check.
        Returns derived state for comparison against persisted state.
        """
        await self._repo.get_by_id_or_raise(workflow_id)  # 404 guard
        events: list[WorkflowEvent] = await self._events.get_by_workflow(workflow_id)

        derived_status = WorkflowStatus.pending
        derived_step: str | None = None

        for event in events:
            if event.event_type in _STATUS_EVENTS:
                derived_status = _STATUS_EVENTS[event.event_type]
            if event.event_type == "workflow.advanced":
                derived_step = event.payload.get("step")

        return ReplayResult(
            workflow_id=workflow_id,
            replayed_events=len(events),
            final_status=derived_status,
            final_step=derived_step,
        )
