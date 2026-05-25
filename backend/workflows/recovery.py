"""
Workflow recovery: resume failed/paused workflows and replay event history.

Recovery is deterministic: given the same event log, same state is produced.
No side effects beyond DB reads (for replay/consistency checks).

Primitives:
  resume_failed          — transition failed workflow back to active
  resume_from_checkpoint — restore execution context from last checkpoint
  replay                 — derive state from event log (read-only)
  consistency_check      — compare persisted state against replayed state
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import AuditActorType, WorkflowStatus
from models.workflow import Workflow
from models.workflow_event import WorkflowEvent
from workflows.checkpoint import CheckpointRuntime
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
    "workflow.recovery.resumed": WorkflowStatus.active,
    "workflow.recovery.checkpoint_restored": WorkflowStatus.active,
}


@dataclass(frozen=True)
class ReplayResult:
    workflow_id: UUID
    replayed_events: int
    final_status: WorkflowStatus
    final_step: str | None


@dataclass(frozen=True)
class CheckpointRecoveryResult:
    workflow_id: UUID
    restored_from_step: str
    restored_payload: dict
    workflow: Workflow


@dataclass(frozen=True)
class ConsistencyResult:
    workflow_id: UUID
    persisted_status: WorkflowStatus
    derived_status: WorkflowStatus
    persisted_step: str | None
    derived_step: str | None
    is_consistent: bool


class WorkflowRecovery:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)
        self._events = WorkflowEventRepository(session)
        self._checkpoints = CheckpointRuntime(session)

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

    async def resume_from_checkpoint(
        self,
        workflow_id: UUID,
        actor_id: UUID | None = None,
    ) -> CheckpointRecoveryResult:
        """
        Restore a failed/paused workflow to active using the latest checkpoint.
        Sets current_step from checkpoint and emits a recovery event.
        Raises TransitionError if no checkpoints exist or workflow is terminal.
        """
        checkpoint = await self._checkpoints.get_latest(workflow_id)
        if checkpoint is None:
            raise TransitionError(
                workflow_id,
                WorkflowStatus.failed,  # placeholder — caller knows actual status
                WorkflowStatus.active,
                reason="no checkpoint found — cannot resume from checkpoint",
            )

        workflow = await self._repo.get_for_update_or_raise(workflow_id)

        terminal = {WorkflowStatus.completed, WorkflowStatus.cancelled}
        if workflow.workflow_status in terminal:
            raise TransitionError(
                workflow_id,
                workflow.workflow_status,
                WorkflowStatus.active,
                reason=f"{workflow.workflow_status} is terminal — cannot resume",
            )

        workflow.workflow_status = WorkflowStatus.active
        workflow.current_step = checkpoint.step
        self._session.add(workflow)
        await self._session.flush()

        await self._events.append_event(
            workflow_id=workflow.id,
            event_type="workflow.recovery.checkpoint_restored",
            payload={
                "restored_from_step": checkpoint.step,
                "status_at_checkpoint": checkpoint.status_at_checkpoint,
                "checkpoint_payload": checkpoint.payload,
            },
            actor_type=AuditActorType.system,
            actor_id=actor_id,
            correlation_id=workflow.correlation_id,
        )

        return CheckpointRecoveryResult(
            workflow_id=workflow_id,
            restored_from_step=checkpoint.step,
            restored_payload=checkpoint.payload,
            workflow=workflow,
        )

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
            if event.event_type in ("workflow.advanced", "workflow.recovery.checkpoint_restored"):
                derived_step = (
                    event.payload.get("step")
                    or event.payload.get("restored_from_step")
                )

        return ReplayResult(
            workflow_id=workflow_id,
            replayed_events=len(events),
            final_status=derived_status,
            final_step=derived_step,
        )

    async def consistency_check(self, workflow_id: UUID) -> ConsistencyResult:
        """
        Compare persisted state against event-log-derived state.
        Does NOT mutate DB. Use for validation and diagnostics.
        """
        workflow = await self._repo.get_by_id_or_raise(workflow_id)
        replay = await self.replay(workflow_id)

        return ConsistencyResult(
            workflow_id=workflow_id,
            persisted_status=workflow.workflow_status,
            derived_status=replay.final_status,
            persisted_step=workflow.current_step,
            derived_step=replay.final_step,
            is_consistent=(
                workflow.workflow_status == replay.final_status
                and workflow.current_step == replay.final_step
            ),
        )
