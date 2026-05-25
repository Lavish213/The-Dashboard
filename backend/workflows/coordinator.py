"""
RollbackCoordinator — deterministic, idempotent workflow rollback orchestration.

Responsibilities:
  1. Idempotency guard: if workflow is already terminal, return was_idempotent=True
  2. Checkpoint lookup: find last known-good step for audit context
  3. WorkflowRollback.rollback(): state transition + workflow_event
  4. Domain event: emit workflow.rollback.coordinated to domain_events for replay
  5. Compensating action audit: record each action as a workflow_event (no execution)
  6. Governance hooks: rollback_on_approval_expiry / rollback_on_approval_rejection

Governance hooks are entry points for:
  - ApprovalExpiryRuntime (approval expired → rollback)
  - ApprovalEscalationRuntime (escalation failed → rollback)
  - WorkflowRuntime (cancellation with compensation)
  - Future: reconnect recovery, interrupted execution

Invariants:
  - Never executes compensating actions — records them only
  - Never modifies workflow state twice (idempotency guard)
  - Always emits domain event regardless of compensation presence
  - Session commit is caller's responsibility
"""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from events.contracts import DomainEvent
from events.emitter import event_emitter
from models.enums import AuditActorType, WorkflowStatus
from workflows.checkpoint import CheckpointRuntime
from workflows.compensation import CompensatingAction, RollbackResult
from workflows.persistence import WorkflowEventRepository, WorkflowRepository
from workflows.rollback import RollbackError, WorkflowRollback

logger = structlog.get_logger(__name__)

WORKFLOW_CHANNEL = "workflows"
EVT_ROLLBACK_COORDINATED = "workflow.rollback.coordinated"
EVT_COMPENSATING_ACTION = "workflow.compensating_action.recorded"

_TERMINAL: frozenset[WorkflowStatus] = frozenset({
    WorkflowStatus.completed,
    WorkflowStatus.failed,
    WorkflowStatus.cancelled,
})


class RollbackCoordinator:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)
        self._events = WorkflowEventRepository(session)
        self._checkpoints = CheckpointRuntime(session)
        self._rollback = WorkflowRollback(session)

    async def coordinate(
        self,
        workflow_id: UUID,
        reason: str,
        trigger: str,
        actor_type: AuditActorType = AuditActorType.system,
        actor_id: UUID | None = None,
        compensating_actions: list[CompensatingAction] | None = None,
    ) -> RollbackResult:
        """
        Orchestrate a full rollback with audit trail and domain event emission.

        If workflow is already terminal, returns RollbackResult(was_idempotent=True).
        Compensating actions are recorded as audit events — not executed.
        """
        actions = compensating_actions or []

        # Idempotency check — no lock needed, terminal is absorbing
        workflow = await self._repo.get_by_id_or_raise(workflow_id)
        if workflow.workflow_status in _TERMINAL:
            logger.info(
                "rollback.coordinator.idempotent",
                workflow_id=str(workflow_id),
                status=workflow.workflow_status,
                trigger=trigger,
            )
            return RollbackResult(
                workflow_id=workflow_id,
                trigger=trigger,
                reason=reason,
                rolled_back_from_step=workflow.current_step,
                compensating_actions=actions,
                was_idempotent=True,
            )

        # Capture last checkpoint before state change
        checkpoint = await self._checkpoints.get_latest(workflow_id)
        rolled_back_from_step = workflow.current_step

        # Execute rollback (sets cancelled, emits workflow_event)
        try:
            await self._rollback.rollback(
                workflow_id=workflow_id,
                reason=reason,
                actor_type=actor_type,
                actor_id=actor_id,
            )
        except RollbackError:
            # Concurrent terminal transition — treat as idempotent
            return RollbackResult(
                workflow_id=workflow_id,
                trigger=trigger,
                reason=reason,
                rolled_back_from_step=rolled_back_from_step,
                compensating_actions=actions,
                was_idempotent=True,
            )

        # Persist domain event for replay
        domain_payload: dict = {
            "workflow_id": str(workflow_id),
            "trigger": trigger,
            "reason": reason,
            "rolled_back_from_step": rolled_back_from_step,
            "last_checkpoint_step": checkpoint.step if checkpoint else None,
            "compensating_action_count": len(actions),
        }

        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=WORKFLOW_CHANNEL,
                event_type=EVT_ROLLBACK_COORDINATED,
                payload=domain_payload,
                correlation_id=str(workflow.correlation_id),
            ),
        )

        # Record each compensating action as an audit workflow_event (not executed)
        for action in actions:
            await self._events.append_event(
                workflow_id=workflow_id,
                event_type=EVT_COMPENSATING_ACTION,
                payload={
                    "action_type": action.action_type,
                    "target_id": str(action.target_id),
                    "triggered_by": action.triggered_by,
                    "payload": action.payload,
                },
                actor_type=AuditActorType.system,
                actor_id=actor_id,
                correlation_id=workflow.correlation_id,
            )

        logger.info(
            "rollback.coordinator.complete",
            workflow_id=str(workflow_id),
            trigger=trigger,
            step=rolled_back_from_step,
            actions=len(actions),
        )

        return RollbackResult(
            workflow_id=workflow_id,
            trigger=trigger,
            reason=reason,
            rolled_back_from_step=rolled_back_from_step,
            compensating_actions=actions,
            was_idempotent=False,
        )

    # ------------------------------------------------------------------
    # Governance hooks — entry points for approval/escalation triggers
    # ------------------------------------------------------------------

    async def rollback_on_approval_expiry(
        self,
        approval_id: UUID,
        workflow_id: UUID,
        reason: str = "approval_expired",
    ) -> RollbackResult:
        """
        Governance hook: approval expired → rollback workflow.
        Records a cancel_approval compensating action.
        """
        actions = [
            CompensatingAction(
                action_type="cancel_approval",
                target_id=approval_id,
                triggered_by="approval_expired",
                payload={"approval_id": str(approval_id), "reason": reason},
            )
        ]
        return await self.coordinate(
            workflow_id=workflow_id,
            reason=reason,
            trigger="approval_expired",
            actor_type=AuditActorType.system,
            compensating_actions=actions,
        )

    async def rollback_on_approval_rejection(
        self,
        approval_id: UUID,
        workflow_id: UUID,
        rejected_by: UUID | None = None,
        reason: str = "approval_rejected",
    ) -> RollbackResult:
        """
        Governance hook: approval rejected → rollback workflow with audit trail.
        Records a cancel_approval compensating action.
        """
        actions = [
            CompensatingAction(
                action_type="cancel_approval",
                target_id=approval_id,
                triggered_by="approval_rejected",
                payload={
                    "approval_id": str(approval_id),
                    "rejected_by": str(rejected_by) if rejected_by else None,
                    "reason": reason,
                },
            )
        ]
        return await self.coordinate(
            workflow_id=workflow_id,
            reason=reason,
            trigger="approval_rejected",
            actor_type=AuditActorType.system,
            actor_id=rejected_by,
            compensating_actions=actions,
        )

    async def rollback_on_escalation_failure(
        self,
        workflow_id: UUID,
        reason: str = "escalation_unresolved",
    ) -> RollbackResult:
        """
        Governance hook: escalated approval unresolved beyond threshold → rollback.
        """
        return await self.coordinate(
            workflow_id=workflow_id,
            reason=reason,
            trigger="escalation_unresolved",
            actor_type=AuditActorType.system,
        )
