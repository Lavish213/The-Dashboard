"""
Workflow runtime engine.

Handles: start, advance, pause, resume, complete, fail, cancel.
Emits append-only events via WorkflowEventRepository after every mutation.
No hidden state. No side effects outside DB.
"""

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import AuditActorType, WorkflowStatus, WorkflowType
from models.workflow import Workflow
from workflows.persistence import WorkflowEventRepository, WorkflowRepository
from workflows.transitions import TransitionError, validate_transition

# Event type constants
EVT_WORKFLOW_STARTED = "workflow.started"
EVT_WORKFLOW_ADVANCED = "workflow.advanced"
EVT_WORKFLOW_PAUSED = "workflow.paused"
EVT_WORKFLOW_RESUMED = "workflow.resumed"
EVT_WORKFLOW_COMPLETED = "workflow.completed"
EVT_WORKFLOW_FAILED = "workflow.failed"
EVT_WORKFLOW_CANCELLED = "workflow.cancelled"


class WorkflowRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)
        self._events = WorkflowEventRepository(session)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def start(
        self,
        workflow_type: WorkflowType,
        lead_id: UUID | None = None,
        initiated_by: UUID | None = None,
        actor_type: AuditActorType = AuditActorType.user,
        correlation_id: UUID | None = None,
    ) -> Workflow:
        """Create and activate a new workflow."""
        corr_id = correlation_id or uuid4()

        workflow = await self._repo.create(
            workflow_type=workflow_type,
            workflow_status=WorkflowStatus.active,
            lead_id=lead_id,
            initiated_by=initiated_by,
            correlation_id=corr_id,
        )

        await self._emit(
            workflow=workflow,
            event_type=EVT_WORKFLOW_STARTED,
            payload={"workflow_type": workflow_type, "lead_id": str(lead_id) if lead_id else None},
            actor_type=actor_type,
            actor_id=initiated_by,
        )

        return workflow

    async def advance(
        self,
        workflow_id: UUID,
        step: str,
        payload: dict | None = None,
        actor_type: AuditActorType = AuditActorType.system,
        actor_id: UUID | None = None,
    ) -> Workflow:
        """Move workflow to next step (must already be active)."""
        workflow = await self._repo.get_for_update_or_raise(workflow_id)
        self._assert_active(workflow)

        workflow.current_step = step
        self._session.add(workflow)
        await self._session.flush()

        await self._emit(
            workflow=workflow,
            event_type=EVT_WORKFLOW_ADVANCED,
            payload={"step": step, **(payload or {})},
            actor_type=actor_type,
            actor_id=actor_id,
        )

        return workflow

    async def pause(
        self,
        workflow_id: UUID,
        reason: str = "",
        actor_type: AuditActorType = AuditActorType.user,
        actor_id: UUID | None = None,
    ) -> Workflow:
        return await self._transition(
            workflow_id=workflow_id,
            target=WorkflowStatus.paused,
            event_type=EVT_WORKFLOW_PAUSED,
            payload={"reason": reason},
            actor_type=actor_type,
            actor_id=actor_id,
        )

    async def resume(
        self,
        workflow_id: UUID,
        actor_type: AuditActorType = AuditActorType.user,
        actor_id: UUID | None = None,
    ) -> Workflow:
        return await self._transition(
            workflow_id=workflow_id,
            target=WorkflowStatus.active,
            event_type=EVT_WORKFLOW_RESUMED,
            payload={},
            actor_type=actor_type,
            actor_id=actor_id,
        )

    async def complete(
        self,
        workflow_id: UUID,
        payload: dict | None = None,
        actor_type: AuditActorType = AuditActorType.system,
        actor_id: UUID | None = None,
    ) -> Workflow:
        return await self._transition(
            workflow_id=workflow_id,
            target=WorkflowStatus.completed,
            event_type=EVT_WORKFLOW_COMPLETED,
            payload=payload or {},
            actor_type=actor_type,
            actor_id=actor_id,
        )

    async def fail(
        self,
        workflow_id: UUID,
        reason: str,
        actor_type: AuditActorType = AuditActorType.system,
        actor_id: UUID | None = None,
    ) -> Workflow:
        return await self._transition(
            workflow_id=workflow_id,
            target=WorkflowStatus.failed,
            event_type=EVT_WORKFLOW_FAILED,
            payload={"reason": reason},
            actor_type=actor_type,
            actor_id=actor_id,
        )

    async def cancel(
        self,
        workflow_id: UUID,
        reason: str = "",
        actor_type: AuditActorType = AuditActorType.user,
        actor_id: UUID | None = None,
    ) -> Workflow:
        return await self._transition(
            workflow_id=workflow_id,
            target=WorkflowStatus.cancelled,
            event_type=EVT_WORKFLOW_CANCELLED,
            payload={"reason": reason},
            actor_type=actor_type,
            actor_id=actor_id,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _transition(
        self,
        workflow_id: UUID,
        target: WorkflowStatus,
        event_type: str,
        payload: dict,
        actor_type: AuditActorType,
        actor_id: UUID | None,
    ) -> Workflow:
        workflow = await self._repo.get_for_update_or_raise(workflow_id)
        validate_transition(workflow_id, workflow.workflow_status, target)

        workflow.workflow_status = target
        self._session.add(workflow)
        await self._session.flush()

        await self._emit(
            workflow=workflow,
            event_type=event_type,
            payload=payload,
            actor_type=actor_type,
            actor_id=actor_id,
        )

        return workflow

    async def _emit(
        self,
        workflow: Workflow,
        event_type: str,
        payload: dict,
        actor_type: AuditActorType,
        actor_id: UUID | None,
    ) -> None:
        await self._events.append_event(
            workflow_id=workflow.id,
            event_type=event_type,
            payload=payload,
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=workflow.correlation_id,
        )

    @staticmethod
    def _assert_active(workflow: Workflow) -> None:
        if workflow.workflow_status != WorkflowStatus.active:
            raise TransitionError(
                workflow.id,
                workflow.workflow_status,
                WorkflowStatus.active,
                reason="workflow must be active to advance",
            )
