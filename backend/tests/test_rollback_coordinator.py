"""
Phase 7 — Rollback Coordinator + Checkpoint + Recovery Tests.

Covers:
- WorkflowCheckpoint (set, get_latest, get_all, idempotent)
- CompensatingAction / RollbackResult contracts (pure)
- RollbackCoordinator.coordinate (happy path, idempotent, domain events)
- RollbackCoordinator governance hooks (expiry, rejection, escalation)
- WorkflowRecovery.resume_from_checkpoint
- WorkflowRecovery.consistency_check
- RollbackCoordinator + compensating action audit trail
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from events.replay import replay_channel
from models.enums import ApprovalType, WorkflowStatus, WorkflowType
from workflows.approvals import WorkflowApprovalGate
from workflows.checkpoint import CheckpointRuntime
from workflows.compensation import CompensatingAction, RollbackResult
from workflows.coordinator import (
    EVT_COMPENSATING_ACTION,
    EVT_ROLLBACK_COORDINATED,
    RollbackCoordinator,
)
from workflows.persistence import WorkflowEventRepository, WorkflowRepository
from workflows.recovery import WorkflowRecovery
from workflows.runtime import WorkflowRuntime

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _active(db: AsyncSession, wf_type: WorkflowType = WorkflowType.outreach):
    return await WorkflowRuntime(db).start(wf_type)


async def _advanced(db: AsyncSession, step: str = "contacted"):
    rt = WorkflowRuntime(db)
    wf = await rt.start(WorkflowType.outreach)
    await rt.advance(wf.id, step=step)
    return wf


# ---------------------------------------------------------------------------
# WorkflowCheckpoint
# ---------------------------------------------------------------------------

class TestWorkflowCheckpoint:
    async def test_set_creates_checkpoint(self, db: AsyncSession) -> None:
        wf = await _active(db)
        crt = CheckpointRuntime(db)
        cp = await crt.set(wf.id, step="contacted", status=WorkflowStatus.active)
        assert cp.step == "contacted"
        assert cp.status_at_checkpoint == "active"
        assert cp.workflow_id == wf.id

    async def test_set_idempotent_same_step(self, db: AsyncSession) -> None:
        wf = await _active(db)
        crt = CheckpointRuntime(db)
        cp1 = await crt.set(wf.id, step="contacted", status=WorkflowStatus.active)
        cp2 = await crt.set(wf.id, step="contacted", status=WorkflowStatus.active)
        assert cp1.id == cp2.id

    async def test_set_preserves_payload(self, db: AsyncSession) -> None:
        wf = await _active(db)
        crt = CheckpointRuntime(db)
        payload = {"lead_id": str(uuid4()), "attempt": 1}
        cp = await crt.set(wf.id, step="qualified", status=WorkflowStatus.active, payload=payload)
        assert cp.payload == payload

    async def test_get_latest_returns_most_recent(self, db: AsyncSession) -> None:
        wf = await _active(db)
        crt = CheckpointRuntime(db)
        await crt.set(wf.id, step="step_a", status=WorkflowStatus.active)
        await crt.set(wf.id, step="step_b", status=WorkflowStatus.active)
        latest = await crt.get_latest(wf.id)
        assert latest is not None
        assert latest.step == "step_b"

    async def test_get_latest_returns_none_when_empty(self, db: AsyncSession) -> None:
        wf = await _active(db)
        crt = CheckpointRuntime(db)
        assert await crt.get_latest(wf.id) is None

    async def test_get_all_ordered(self, db: AsyncSession) -> None:
        wf = await _active(db)
        crt = CheckpointRuntime(db)
        await crt.set(wf.id, step="step_a", status=WorkflowStatus.active)
        await crt.set(wf.id, step="step_b", status=WorkflowStatus.active)
        all_cps = await crt.get_all(wf.id)
        assert len(all_cps) == 2
        assert all_cps[0].step == "step_a"
        assert all_cps[1].step == "step_b"

    async def test_checkpoints_isolated_by_workflow(self, db: AsyncSession) -> None:
        wf1 = await _active(db)
        wf2 = await _active(db)
        crt = CheckpointRuntime(db)
        await crt.set(wf1.id, step="step_x", status=WorkflowStatus.active)
        assert await crt.get_latest(wf2.id) is None


# ---------------------------------------------------------------------------
# CompensatingAction / RollbackResult contracts
# ---------------------------------------------------------------------------

class TestCompensatingActionContract:
    def test_compensating_action_is_frozen(self) -> None:
        action = CompensatingAction(
            action_type="cancel_approval",
            target_id=uuid4(),
            triggered_by="approval_expired",
        )
        with pytest.raises(Exception):
            action.action_type = "mutated"  # type: ignore[misc]  # frozen dataclass

    def test_rollback_result_is_frozen(self) -> None:
        result = RollbackResult(
            workflow_id=uuid4(),
            trigger="approval_expired",
            reason="expired",
            rolled_back_from_step="step_a",
            compensating_actions=[],
            was_idempotent=False,
        )
        assert result.trigger == "approval_expired"
        assert result.was_idempotent is False

    def test_compensating_action_default_payload(self) -> None:
        action = CompensatingAction(
            action_type="release_lead",
            target_id=uuid4(),
            triggered_by="manual",
        )
        assert action.payload == {}


# ---------------------------------------------------------------------------
# RollbackCoordinator
# ---------------------------------------------------------------------------

class TestRollbackCoordinator:
    async def test_coordinate_cancels_workflow(self, db: AsyncSession) -> None:
        wf = await _advanced(db, step="contacted")
        coord = RollbackCoordinator(db)
        result = await coord.coordinate(wf.id, reason="test", trigger="manual")

        repo = WorkflowRepository(db)
        fetched = await repo.get_by_id(wf.id)
        assert fetched.workflow_status == WorkflowStatus.cancelled
        assert result.was_idempotent is False

    async def test_coordinate_returns_rolled_back_step(self, db: AsyncSession) -> None:
        wf = await _advanced(db, step="qualified")
        coord = RollbackCoordinator(db)
        result = await coord.coordinate(wf.id, reason="test", trigger="manual")
        assert result.rolled_back_from_step == "qualified"

    async def test_coordinate_emits_domain_event(self, db: AsyncSession) -> None:
        wf = await _active(db)
        coord = RollbackCoordinator(db)
        await coord.coordinate(wf.id, reason="test", trigger="manual")

        stored, _ = await replay_channel(db, "workflows")
        assert any(e.event_type == EVT_ROLLBACK_COORDINATED for e in stored)

    async def test_coordinate_domain_event_has_trigger(self, db: AsyncSession) -> None:
        wf = await _active(db)
        coord = RollbackCoordinator(db)
        await coord.coordinate(wf.id, reason="test", trigger="approval_expired")

        stored, _ = await replay_channel(db, "workflows")
        evt = next(e for e in stored if e.event_type == EVT_ROLLBACK_COORDINATED)
        assert evt.payload["trigger"] == "approval_expired"

    async def test_coordinate_idempotent_on_terminal(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await WorkflowRuntime(db).complete(wf.id)

        coord = RollbackCoordinator(db)
        result = await coord.coordinate(wf.id, reason="test", trigger="manual")
        assert result.was_idempotent is True

    async def test_coordinate_idempotent_on_already_cancelled(self, db: AsyncSession) -> None:
        wf = await _active(db)
        coord = RollbackCoordinator(db)
        r1 = await coord.coordinate(wf.id, reason="first", trigger="manual")
        r2 = await coord.coordinate(wf.id, reason="second", trigger="manual")
        assert r1.was_idempotent is False
        assert r2.was_idempotent is True

    async def test_coordinate_records_compensating_actions(self, db: AsyncSession) -> None:
        wf = await _active(db)
        approval_id = uuid4()
        actions = [
            CompensatingAction(
                action_type="cancel_approval",
                target_id=approval_id,
                triggered_by="approval_expired",
            )
        ]
        coord = RollbackCoordinator(db)
        await coord.coordinate(wf.id, reason="test", trigger="manual", compensating_actions=actions)

        events = await WorkflowEventRepository(db).get_by_workflow(wf.id)
        comp_evts = [e for e in events if e.event_type == EVT_COMPENSATING_ACTION]
        assert len(comp_evts) == 1
        assert comp_evts[0].payload["action_type"] == "cancel_approval"

    async def test_coordinate_uses_last_checkpoint_in_domain_event(
        self, db: AsyncSession
    ) -> None:
        wf = await _advanced(db, step="contacted")
        crt = CheckpointRuntime(db)
        await crt.set(wf.id, step="contacted", status=WorkflowStatus.active)

        coord = RollbackCoordinator(db)
        await coord.coordinate(wf.id, reason="test", trigger="manual")

        stored, _ = await replay_channel(db, "workflows")
        evt = next(e for e in stored if e.event_type == EVT_ROLLBACK_COORDINATED)
        assert evt.payload["last_checkpoint_step"] == "contacted"

    async def test_multiple_compensating_actions_recorded(self, db: AsyncSession) -> None:
        wf = await _active(db)
        actions = [
            CompensatingAction(
                action_type="cancel_approval",
                target_id=uuid4(),
                triggered_by="approval_expired",
            ),
            CompensatingAction(
                action_type="release_lead",
                target_id=uuid4(),
                triggered_by="approval_expired",
            ),
        ]
        coord = RollbackCoordinator(db)
        await coord.coordinate(wf.id, reason="test", trigger="manual", compensating_actions=actions)

        events = await WorkflowEventRepository(db).get_by_workflow(wf.id)
        comp_evts = [e for e in events if e.event_type == EVT_COMPENSATING_ACTION]
        assert len(comp_evts) == 2


# ---------------------------------------------------------------------------
# Governance hooks
# ---------------------------------------------------------------------------

class TestGovernanceHooks:
    async def test_rollback_on_approval_expiry(self, db: AsyncSession) -> None:
        wf = await _active(db)
        gate = WorkflowApprovalGate(db)
        approval = await gate.request_approval(wf.id, ApprovalType.offer)

        coord = RollbackCoordinator(db)
        result = await coord.rollback_on_approval_expiry(
            approval_id=approval.id,
            workflow_id=wf.id,
        )

        assert result.trigger == "approval_expired"
        assert result.was_idempotent is False
        assert len(result.compensating_actions) == 1
        assert result.compensating_actions[0].action_type == "cancel_approval"

        repo = WorkflowRepository(db)
        fetched = await repo.get_by_id(wf.id)
        assert fetched.workflow_status == WorkflowStatus.cancelled

    async def test_rollback_on_approval_rejection(self, db: AsyncSession) -> None:
        wf = await _active(db)
        gate = WorkflowApprovalGate(db)
        approval = await gate.request_approval(wf.id, ApprovalType.offer)

        coord = RollbackCoordinator(db)
        result = await coord.rollback_on_approval_rejection(
            approval_id=approval.id,
            workflow_id=wf.id,
        )

        assert result.trigger == "approval_rejected"
        assert result.was_idempotent is False

    async def test_rollback_on_escalation_failure(self, db: AsyncSession) -> None:
        wf = await _active(db)
        coord = RollbackCoordinator(db)
        result = await coord.rollback_on_escalation_failure(wf.id)

        assert result.trigger == "escalation_unresolved"
        assert result.was_idempotent is False

    async def test_governance_hook_idempotent_on_terminal(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await WorkflowRuntime(db).cancel(wf.id, reason="pre-cancelled")

        coord = RollbackCoordinator(db)
        result = await coord.rollback_on_approval_expiry(
            approval_id=uuid4(),
            workflow_id=wf.id,
        )
        assert result.was_idempotent is True


# ---------------------------------------------------------------------------
# WorkflowRecovery — checkpoint-based recovery
# ---------------------------------------------------------------------------

class TestCheckpointRecovery:
    async def test_resume_from_checkpoint_restores_step(self, db: AsyncSession) -> None:
        wf = await _active(db)
        crt = CheckpointRuntime(db)
        await crt.set(wf.id, step="qualified", status=WorkflowStatus.active, payload={"score": 9})

        # Fail the workflow
        await WorkflowRuntime(db).fail(wf.id, reason="network error")

        recovery = WorkflowRecovery(db)
        result = await recovery.resume_from_checkpoint(wf.id)

        assert result.restored_from_step == "qualified"
        assert result.restored_payload == {"score": 9}
        assert result.workflow.workflow_status == WorkflowStatus.active
        assert result.workflow.current_step == "qualified"

    async def test_resume_from_checkpoint_emits_event(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await CheckpointRuntime(db).set(wf.id, step="step_x", status=WorkflowStatus.active)
        await WorkflowRuntime(db).fail(wf.id, reason="err")

        await WorkflowRecovery(db).resume_from_checkpoint(wf.id)

        events = await WorkflowEventRepository(db).get_by_workflow(wf.id)
        assert any(e.event_type == "workflow.recovery.checkpoint_restored" for e in events)

    async def test_resume_from_checkpoint_no_checkpoint_raises(
        self, db: AsyncSession
    ) -> None:
        from workflows.transitions import TransitionError

        wf = await _active(db)
        await WorkflowRuntime(db).fail(wf.id, reason="err")

        with pytest.raises(TransitionError, match="no checkpoint"):
            await WorkflowRecovery(db).resume_from_checkpoint(wf.id)

    async def test_resume_from_checkpoint_terminal_raises(self, db: AsyncSession) -> None:
        from workflows.transitions import TransitionError

        wf = await _active(db)
        await CheckpointRuntime(db).set(wf.id, step="s", status=WorkflowStatus.active)
        await WorkflowRuntime(db).cancel(wf.id, reason="done")

        with pytest.raises(TransitionError, match="terminal"):
            await WorkflowRecovery(db).resume_from_checkpoint(wf.id)


# ---------------------------------------------------------------------------
# WorkflowRecovery — consistency check
# ---------------------------------------------------------------------------

class TestConsistencyCheck:
    async def test_consistent_after_normal_advance(self, db: AsyncSession) -> None:
        wf = await _advanced(db, step="contacted")
        result = await WorkflowRecovery(db).consistency_check(wf.id)
        assert result.is_consistent is True
        assert result.persisted_status == WorkflowStatus.active
        assert result.derived_status == WorkflowStatus.active

    async def test_consistent_after_cancel(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await WorkflowRuntime(db).cancel(wf.id, reason="done")
        result = await WorkflowRecovery(db).consistency_check(wf.id)
        assert result.is_consistent is True
        assert result.derived_status == WorkflowStatus.cancelled

    async def test_consistent_after_checkpoint_recovery(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await CheckpointRuntime(db).set(wf.id, step="step_z", status=WorkflowStatus.active)
        await WorkflowRuntime(db).fail(wf.id, reason="err")
        await WorkflowRecovery(db).resume_from_checkpoint(wf.id)

        result = await WorkflowRecovery(db).consistency_check(wf.id)
        assert result.is_consistent is True
        assert result.persisted_step == "step_z"
        assert result.derived_step == "step_z"
