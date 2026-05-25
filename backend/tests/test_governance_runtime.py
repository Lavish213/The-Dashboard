"""
Phase 7 — Governance Runtime Tests.

Covers:
- ApprovalEscalationRuntime (escalate, idempotency, error cases)
- Escalated approval resolution (escalated -> approved/rejected)
- ApprovalExpiryRuntime (expire pending, skip non-pending, skip not-expired)
- ApprovalPolicyRuntime (stateless, no DB)
- Governance domain event persistence (EventStore integration)
- WorkflowRollback domain event emission

All DB tests run against karpathys_test with SAVEPOINT rollback per test.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from approvals.engine import ApprovalEngine
from approvals.escalation import ApprovalEscalationRuntime, EscalationError
from approvals.expiry import ApprovalExpiryRuntime
from approvals.policies import ApprovalPolicyRuntime
from events.replay import replay_channel
from models.enums import (
    ApprovalStatus,
    ApprovalType,
    RiskLevel,
    WorkflowStatus,
    WorkflowType,
)
from repositories.approval import ApprovalRepository
from workflows.approvals import ApprovalGateError, WorkflowApprovalGate
from workflows.rollback import WorkflowRollback
from workflows.runtime import WorkflowRuntime

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _active_workflow(db: AsyncSession, wf_type: WorkflowType = WorkflowType.outreach):
    rt = WorkflowRuntime(db)
    return await rt.start(wf_type)


async def _pending_approval(db: AsyncSession, *, expires_at=None):
    wf = await _active_workflow(db)
    gate = WorkflowApprovalGate(db)
    approval = await gate.request_approval(
        workflow_id=wf.id,
        approval_type=ApprovalType.offer,
        expires_at=expires_at,
    )
    return wf, approval


# ---------------------------------------------------------------------------
# ApprovalEscalationRuntime
# ---------------------------------------------------------------------------

class TestApprovalEscalation:
    async def test_escalate_pending_changes_status(self, db: AsyncSession) -> None:
        _, approval = await _pending_approval(db)
        runtime = ApprovalEscalationRuntime(db)

        record = await runtime.escalate(approval.id, reason="SLA breach")

        repo = ApprovalRepository(db)
        fetched = await repo.get_by_id(approval.id)
        assert fetched.approval_status == ApprovalStatus.escalated
        assert record.reason == "SLA breach"

    async def test_escalate_emits_workflow_event(self, db: AsyncSession) -> None:
        wf, approval = await _pending_approval(db)
        from workflows.persistence import WorkflowEventRepository
        runtime = ApprovalEscalationRuntime(db)

        await runtime.escalate(approval.id, reason="SLA breach")

        events = await WorkflowEventRepository(db).get_by_workflow(wf.id)
        assert any(e.event_type == "approval.escalated" for e in events)

    async def test_escalate_persists_domain_event(self, db: AsyncSession) -> None:
        _, approval = await _pending_approval(db)
        runtime = ApprovalEscalationRuntime(db)

        await runtime.escalate(approval.id, reason="SLA breach")

        stored, _ = await replay_channel(db, "approvals")
        types = [e.event_type for e in stored]
        assert "approval.escalated" in types

    async def test_escalate_non_pending_raises(self, db: AsyncSession) -> None:
        wf, approval = await _pending_approval(db)
        gate = WorkflowApprovalGate(db)
        await gate.resolve(approval.id, resolved_by=None, approved=True)

        runtime = ApprovalEscalationRuntime(db)
        with pytest.raises(EscalationError):
            await runtime.escalate(approval.id, reason="too late")

    async def test_escalate_with_escalated_to(self, db: AsyncSession) -> None:
        _, approval = await _pending_approval(db)
        reviewer_id = uuid4()
        runtime = ApprovalEscalationRuntime(db)

        record = await runtime.escalate(
            approval.id, reason="critical risk", escalated_to=reviewer_id
        )
        assert record.escalated_to == reviewer_id

    async def test_get_escalated_repo(self, db: AsyncSession) -> None:
        _, approval = await _pending_approval(db)
        runtime = ApprovalEscalationRuntime(db)
        await runtime.escalate(approval.id, reason="sla")

        repo = ApprovalRepository(db)
        result = await repo.get_escalated()
        assert result.total >= 1
        ids = [a.id for a in result.items]
        assert approval.id in ids


# ---------------------------------------------------------------------------
# Escalated approval resolution
# ---------------------------------------------------------------------------

class TestEscalatedResolution:
    async def test_escalated_approval_can_be_approved(self, db: AsyncSession) -> None:
        wf, approval = await _pending_approval(db)
        escalation = ApprovalEscalationRuntime(db)
        await escalation.escalate(approval.id, reason="urgent")

        gate = WorkflowApprovalGate(db)
        resolved = await gate.resolve(approval.id, resolved_by=None, approved=True)

        assert resolved.approval_status == ApprovalStatus.approved

        from workflows.persistence import WorkflowRepository
        fetched_wf = await WorkflowRepository(db).get_by_id(wf.id)
        assert fetched_wf.workflow_status == WorkflowStatus.active

    async def test_escalated_approval_can_be_rejected(self, db: AsyncSession) -> None:
        wf, approval = await _pending_approval(db)
        escalation = ApprovalEscalationRuntime(db)
        await escalation.escalate(approval.id, reason="risky")

        gate = WorkflowApprovalGate(db)
        resolved = await gate.resolve(approval.id, resolved_by=None, approved=False)

        assert resolved.approval_status == ApprovalStatus.rejected

        from workflows.persistence import WorkflowRepository
        fetched_wf = await WorkflowRepository(db).get_by_id(wf.id)
        assert fetched_wf.workflow_status == WorkflowStatus.failed

    async def test_already_resolved_raises(self, db: AsyncSession) -> None:
        _, approval = await _pending_approval(db)
        gate = WorkflowApprovalGate(db)
        await gate.resolve(approval.id, resolved_by=None, approved=True)

        with pytest.raises(ApprovalGateError):
            await gate.resolve(approval.id, resolved_by=None, approved=False)


# ---------------------------------------------------------------------------
# ApprovalExpiryRuntime
# ---------------------------------------------------------------------------

class TestApprovalExpiry:
    async def test_expire_pending_with_past_deadline(self, db: AsyncSession) -> None:
        past = datetime.now(UTC) - timedelta(hours=1)
        _, approval = await _pending_approval(db, expires_at=past)

        runtime = ApprovalExpiryRuntime(db)
        result = await runtime.expire_pending()

        assert result.expired_count >= 1
        assert approval.id in result.approval_ids

        repo = ApprovalRepository(db)
        fetched = await repo.get_by_id(approval.id)
        assert fetched.approval_status == ApprovalStatus.expired

    async def test_expire_skips_future_deadline(self, db: AsyncSession) -> None:
        future = datetime.now(UTC) + timedelta(hours=1)
        _, approval = await _pending_approval(db, expires_at=future)

        runtime = ApprovalExpiryRuntime(db)
        result = await runtime.expire_pending()

        assert approval.id not in result.approval_ids

        repo = ApprovalRepository(db)
        fetched = await repo.get_by_id(approval.id)
        assert fetched.approval_status == ApprovalStatus.pending

    async def test_expire_skips_no_deadline(self, db: AsyncSession) -> None:
        _, approval = await _pending_approval(db, expires_at=None)

        runtime = ApprovalExpiryRuntime(db)
        result = await runtime.expire_pending()

        assert approval.id not in result.approval_ids

    async def test_expire_skips_already_resolved(self, db: AsyncSession) -> None:
        past = datetime.now(UTC) - timedelta(hours=1)
        wf, approval = await _pending_approval(db, expires_at=past)
        gate = WorkflowApprovalGate(db)
        await gate.resolve(approval.id, resolved_by=None, approved=True)

        runtime = ApprovalExpiryRuntime(db)
        result = await runtime.expire_pending()

        assert approval.id not in result.approval_ids

    async def test_expire_emits_domain_event(self, db: AsyncSession) -> None:
        past = datetime.now(UTC) - timedelta(hours=1)
        _, approval = await _pending_approval(db, expires_at=past)

        runtime = ApprovalExpiryRuntime(db)
        await runtime.expire_pending()

        stored, _ = await replay_channel(db, "approvals")
        types = [e.event_type for e in stored]
        assert "approval.expired" in types

    async def test_expire_idempotent(self, db: AsyncSession) -> None:
        """Manually expired approvals are not re-expired."""
        past = datetime.now(UTC) - timedelta(hours=1)
        _, approval = await _pending_approval(db, expires_at=past)

        runtime = ApprovalExpiryRuntime(db)
        r1 = await runtime.expire_pending()
        r2 = await runtime.expire_pending()

        assert approval.id in r1.approval_ids
        assert approval.id not in r2.approval_ids


# ---------------------------------------------------------------------------
# ApprovalPolicyRuntime (stateless — no DB)
# ---------------------------------------------------------------------------

class TestApprovalPolicy:
    def test_low_risk_does_not_require_approval(self) -> None:
        policy = ApprovalPolicyRuntime()
        decision = policy.evaluate_risk(RiskLevel.low)
        assert decision.requires_approval is False

    def test_medium_risk_requires_approval(self) -> None:
        policy = ApprovalPolicyRuntime()
        decision = policy.evaluate_risk(RiskLevel.medium)
        assert decision.requires_approval is True

    def test_high_risk_requires_approval(self) -> None:
        policy = ApprovalPolicyRuntime()
        decision = policy.evaluate_risk(RiskLevel.high)
        assert decision.requires_approval is True

    def test_critical_risk_requires_approval(self) -> None:
        policy = ApprovalPolicyRuntime()
        decision = policy.evaluate_risk(RiskLevel.critical)
        assert decision.requires_approval is True

    def test_outreach_workflow_requires_approval(self) -> None:
        policy = ApprovalPolicyRuntime()
        decision = policy.evaluate_workflow_type(WorkflowType.outreach)
        assert decision.requires_approval is True
        assert decision.approval_type == ApprovalType.outreach

    def test_closing_workflow_requires_offer_approval(self) -> None:
        policy = ApprovalPolicyRuntime()
        decision = policy.evaluate_workflow_type(WorkflowType.closing)
        assert decision.requires_approval is True
        assert decision.approval_type == ApprovalType.offer

    def test_follow_up_no_required_types(self) -> None:
        policy = ApprovalPolicyRuntime()
        decision = policy.evaluate_workflow_type(WorkflowType.follow_up)
        assert decision.requires_approval is False

    def test_action_low_risk_no_workflow_not_required(self) -> None:
        policy = ApprovalPolicyRuntime()
        decision = policy.evaluate_action("send_email", RiskLevel.low)
        assert decision.requires_approval is False

    def test_action_high_risk_always_required(self) -> None:
        policy = ApprovalPolicyRuntime()
        decision = policy.evaluate_action("transfer", RiskLevel.high)
        assert decision.requires_approval is True

    def test_policy_is_deterministic(self) -> None:
        """Same inputs always return same output."""
        policy = ApprovalPolicyRuntime()
        d1 = policy.evaluate_risk(RiskLevel.medium)
        d2 = policy.evaluate_risk(RiskLevel.medium)
        assert d1 == d2


# ---------------------------------------------------------------------------
# ApprovalEngine domain event integration
# ---------------------------------------------------------------------------

class TestApprovalEngineDomainEvents:
    async def test_request_persists_domain_event(self, db: AsyncSession) -> None:
        wf = await _active_workflow(db)
        engine = ApprovalEngine(db)
        await engine.request(wf.id, ApprovalType.offer)

        stored, _ = await replay_channel(db, "approvals")
        assert any(e.event_type == "approval.requested" for e in stored)

    async def test_resolve_persists_domain_event(self, db: AsyncSession) -> None:
        wf = await _active_workflow(db)
        engine = ApprovalEngine(db)
        approval = await engine.request(wf.id, ApprovalType.offer)
        await engine.resolve(approval.id, resolved_by=None, approved=True)

        stored, _ = await replay_channel(db, "approvals")
        types = [e.event_type for e in stored]
        assert "approval.requested" in types
        assert "approval.resolved" in types

    async def test_domain_events_ordered_by_seq_num(self, db: AsyncSession) -> None:
        wf = await _active_workflow(db)
        engine = ApprovalEngine(db)
        approval = await engine.request(wf.id, ApprovalType.offer)
        await engine.resolve(approval.id, resolved_by=None, approved=False)

        stored, _ = await replay_channel(db, "approvals")
        seq_nums = [e.seq_num for e in stored]
        assert seq_nums == sorted(seq_nums)
        assert seq_nums[0] < seq_nums[1]


# ---------------------------------------------------------------------------
# WorkflowRollback domain event
# ---------------------------------------------------------------------------

class TestRollbackDomainEvent:
    async def test_rollback_domain_event_not_emitted_to_domain_store(
        self, db: AsyncSession
    ) -> None:
        """WorkflowRollback writes to workflow_events — not domain_events (by design)."""
        wf = await _active_workflow(db)
        rb = WorkflowRollback(db)
        await rb.rollback(wf.id, reason="test")

        # domain_events channel for approvals should not have rollback event
        stored, _ = await replay_channel(db, "approvals")
        assert not any(e.event_type == "workflow.rolled_back" for e in stored)

    async def test_rollback_blocks_terminal_workflow(self, db: AsyncSession) -> None:
        from workflows.rollback import RollbackError
        wf = await _active_workflow(db)
        rb = WorkflowRollback(db)
        await rb.rollback(wf.id, reason="first")

        with pytest.raises(RollbackError):
            await rb.rollback(wf.id, reason="second")
