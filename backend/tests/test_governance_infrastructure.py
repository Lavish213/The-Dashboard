"""
Phase 11 — Governance + Approval Runtime infrastructure tests.

Coverage:
  - PolicyEvaluator: pattern matching, most-restrictive wins, no match defaults,
    inheritance resolution, classify_action, inactive policies ignored
  - GovernancePolicyRuntime: create, supersede, archive, get_snapshot,
    duplicate active key raises, get_all_snapshots
  - ApprovalRouter: route records event, resolve_delegate with/without delegation
  - EscalationChainRuntime: escalate, check_timeout, get_current_step, resolve
  - QuorumRuntime: cast_vote, duplicate voter raises, quorum_met event, get_result
  - DelegationRuntime: grant idempotent, revoke, is_authorized, scope filtering
  - FreezeRuntime: activate, deactivate, kill_switch, is_frozen
  - EmergencyOverrideRuntime: apply resolves approval, idempotent, bad status raises
  - GovernanceAuditRuntime: record, get_for_target
  - GovernancePolicySnapshotRuntime: capture, replay_snapshots
  - GovernanceMetricsRuntime: compute period metrics
  - ApprovalHistoryReconstructor: full history reconstruction
  - Repository layer: governance_policy, governance_event, approval_delegation
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from governance.audit import (
    ACTION_POLICY_EVALUATED,
    GovernanceAuditRuntime,
)
from governance.contracts import (
    EscalationStep,
    GovernancePolicySnapshot,
    PolicyEvaluationInput,
)
from governance.delegation import DelegationError, DelegationRuntime
from governance.escalation import EscalationChainRuntime, EscalationError
from governance.evaluator import PolicyEvaluator
from governance.freeze import FreezeRuntime
from governance.metrics import GovernanceMetricsRuntime
from governance.override import EmergencyOverrideRuntime, OverrideError
from governance.policy import GovernancePolicyRuntime, PolicyError
from governance.quorum import QuorumError, QuorumRuntime
from governance.reconstruction import ApprovalHistoryReconstructor
from governance.router import ApprovalRouter
from governance.snapshot import GovernancePolicySnapshotRuntime, SnapshotError
from models.enums import (
    ActionClassification,
    ApprovalRoutingStrategy,
    ApprovalStatus,
    ApprovalType,
    GovernanceEventType,
    GovernancePolicyStatus,
    RiskTier,
    WorkflowStatus,
    WorkflowType,
)
from repositories.approval_delegation import ApprovalDelegationRepository
from repositories.governance_event import GovernanceEventRepository
from repositories.governance_policy import GovernancePolicyRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _snapshot(
    policy_key: str = "test.policy",
    action_patterns: tuple[str, ...] = ("workflow.*",),
    classification: ActionClassification = ActionClassification.restricted,
    risk_tier: RiskTier = RiskTier.elevated,
    routing_strategy: ApprovalRoutingStrategy = ApprovalRoutingStrategy.direct,
    approver_ids: tuple[uuid.UUID, ...] = (),
    escalation_chain: tuple[EscalationStep, ...] = (),
    quorum_required: int = 0,
    timeout_seconds: int = 3600,
    rules: dict | None = None,
    inherited_from: str | None = None,
    version: int = 1,
    status: GovernancePolicyStatus = GovernancePolicyStatus.active,
) -> GovernancePolicySnapshot:
    return GovernancePolicySnapshot(
        snapshot_id=str(uuid4()),
        policy_key=policy_key,
        version=version,
        status=status,
        classification=classification,
        risk_tier=risk_tier,
        action_patterns=action_patterns,
        routing_strategy=routing_strategy,
        approver_ids=approver_ids,
        escalation_chain=escalation_chain,
        quorum_required=quorum_required,
        timeout_seconds=timeout_seconds,
        rules=rules or {},
        inherited_from=inherited_from,
        captured_at=datetime.now(UTC),
    )


async def _make_workflow(db: AsyncSession) -> object:
    from models.workflow import Workflow
    wf = Workflow(workflow_type=WorkflowType.outreach, workflow_status=WorkflowStatus.active)
    db.add(wf)
    await db.flush()
    return wf


async def _make_approval(db: AsyncSession, workflow_id) -> object:
    from models.approval import Approval
    appr = Approval(
        workflow_id=workflow_id,
        approval_type=ApprovalType.outreach,
        approval_status=ApprovalStatus.pending,
    )
    db.add(appr)
    await db.flush()
    return appr


async def _create_policy(
    db: AsyncSession,
    key: str | None = None,
    patterns: list[str] | None = None,
    classification: ActionClassification = ActionClassification.restricted,
    risk_tier: RiskTier = RiskTier.elevated,
) -> object:
    rt = GovernancePolicyRuntime(db)
    return await rt.create(
        policy_key=key or f"p-{uuid4()}",
        action_patterns=patterns or ["workflow.*"],
        classification=classification,
        risk_tier=risk_tier,
    )


# ---------------------------------------------------------------------------
# PolicyEvaluator (pure, no DB)
# ---------------------------------------------------------------------------

class TestPolicyEvaluator:
    def setup_method(self):
        self.ev = PolicyEvaluator()

    def test_no_matching_policy_returns_safe(self):
        inp = PolicyEvaluationInput(action="unknown.action", risk_tier=RiskTier.standard)
        result = self.ev.evaluate(inp, [])
        assert result.classification == ActionClassification.safe
        assert result.requires_approval is False

    def test_wildcard_pattern_matches(self):
        snap = _snapshot(
            action_patterns=("workflow.*",),
            classification=ActionClassification.restricted,
        )
        inp = PolicyEvaluationInput(action="workflow.offer.create", risk_tier=RiskTier.elevated)
        result = self.ev.evaluate(inp, [snap])
        assert result.classification == ActionClassification.restricted
        assert result.requires_approval is True

    def test_exact_pattern_matches(self):
        snap = _snapshot(
            action_patterns=("ai.tool.exec",),
            classification=ActionClassification.privileged,
        )
        inp = PolicyEvaluationInput(action="ai.tool.exec", risk_tier=RiskTier.high)
        result = self.ev.evaluate(inp, [snap])
        assert result.classification == ActionClassification.privileged

    def test_global_wildcard_matches_everything(self):
        snap = _snapshot(
            action_patterns=("*",),
            classification=ActionClassification.restricted,
        )
        inp = PolicyEvaluationInput(action="anything.at.all", risk_tier=RiskTier.standard)
        result = self.ev.evaluate(inp, [snap])
        assert result.classification == ActionClassification.restricted

    def test_most_restrictive_wins(self):
        low = _snapshot(
            policy_key="low",
            action_patterns=("workflow.*",),
            classification=ActionClassification.restricted,
        )
        high = _snapshot(
            policy_key="high",
            action_patterns=("workflow.*",),
            classification=ActionClassification.forbidden,
        )
        inp = PolicyEvaluationInput(action="workflow.something", risk_tier=RiskTier.critical)
        result = self.ev.evaluate(inp, [low, high])
        assert result.classification == ActionClassification.forbidden

    def test_forbidden_does_not_require_approval(self):
        snap = _snapshot(
            action_patterns=("*",),
            classification=ActionClassification.forbidden,
        )
        inp = PolicyEvaluationInput(action="any.action", risk_tier=RiskTier.critical)
        result = self.ev.evaluate(inp, [snap])
        assert result.classification == ActionClassification.forbidden
        assert result.requires_approval is False

    def test_inactive_policy_ignored(self):
        snap = _snapshot(
            action_patterns=("workflow.*",),
            classification=ActionClassification.restricted,
            status=GovernancePolicyStatus.inactive,
        )
        inp = PolicyEvaluationInput(action="workflow.offer", risk_tier=RiskTier.standard)
        result = self.ev.evaluate(inp, [snap])
        assert result.classification == ActionClassification.safe

    def test_superseded_policy_ignored(self):
        snap = _snapshot(
            action_patterns=("workflow.*",),
            classification=ActionClassification.restricted,
            status=GovernancePolicyStatus.superseded,
        )
        inp = PolicyEvaluationInput(action="workflow.offer", risk_tier=RiskTier.standard)
        result = self.ev.evaluate(inp, [snap])
        assert result.classification == ActionClassification.safe

    def test_classify_action_shortcut(self):
        snap = _snapshot(
            action_patterns=("ai.*",),
            classification=ActionClassification.privileged,
        )
        cls = self.ev.classify_action("ai.model.call", [snap])
        assert cls == ActionClassification.privileged

    def test_classify_action_no_match(self):
        cls = self.ev.classify_action("unmatched", [])
        assert cls == ActionClassification.safe

    def test_inheritance_merges_patterns(self):
        parent = _snapshot(
            policy_key="parent",
            action_patterns=("base.*",),
            classification=ActionClassification.restricted,
        )
        child = _snapshot(
            policy_key="child",
            action_patterns=(),
            classification=ActionClassification.privileged,
            inherited_from="parent",
        )
        inp = PolicyEvaluationInput(action="base.something", risk_tier=RiskTier.elevated)
        result = self.ev.evaluate(inp, [parent, child])
        assert result.classification == ActionClassification.privileged

    def test_matched_policy_key_returned(self):
        snap = _snapshot(policy_key="mykey", action_patterns=("test.*",))
        inp = PolicyEvaluationInput(action="test.action", risk_tier=RiskTier.standard)
        result = self.ev.evaluate(inp, [snap])
        assert result.matched_policy_key == "mykey"

    def test_evaluation_id_is_unique(self):
        inp = PolicyEvaluationInput(action="x", risk_tier=RiskTier.standard)
        r1 = self.ev.evaluate(inp, [])
        r2 = self.ev.evaluate(inp, [])
        assert r1.evaluation_id != r2.evaluation_id

    def test_safe_action_no_approval(self):
        snap = _snapshot(
            action_patterns=("safe.*",),
            classification=ActionClassification.safe,
        )
        inp = PolicyEvaluationInput(action="safe.action", risk_tier=RiskTier.standard)
        result = self.ev.evaluate(inp, [snap])
        assert result.requires_approval is False

    def test_restricted_action_requires_approval(self):
        snap = _snapshot(
            action_patterns=("workflow.*",),
            classification=ActionClassification.restricted,
        )
        inp = PolicyEvaluationInput(action="workflow.outreach", risk_tier=RiskTier.elevated)
        result = self.ev.evaluate(inp, [snap])
        assert result.requires_approval is True

    def test_privileged_action_requires_approval(self):
        snap = _snapshot(
            action_patterns=("admin.*",),
            classification=ActionClassification.privileged,
        )
        inp = PolicyEvaluationInput(action="admin.delete", risk_tier=RiskTier.critical)
        result = self.ev.evaluate(inp, [snap])
        assert result.requires_approval is True


# ---------------------------------------------------------------------------
# GovernancePolicyRuntime (DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGovernancePolicyRuntime:
    async def test_create_policy(self, db: AsyncSession):
        rt = GovernancePolicyRuntime(db)
        policy = await rt.create(
            policy_key=f"p-{uuid4()}",
            action_patterns=["workflow.*"],
            classification=ActionClassification.restricted,
            risk_tier=RiskTier.elevated,
        )
        assert policy.id is not None
        assert policy.version == 1
        assert policy.status == GovernancePolicyStatus.active

    async def test_create_duplicate_active_raises(self, db: AsyncSession):
        rt = GovernancePolicyRuntime(db)
        key = f"p-{uuid4()}"
        await rt.create(
            policy_key=key,
            action_patterns=["*"],
            classification=ActionClassification.safe,
            risk_tier=RiskTier.standard,
        )
        with pytest.raises(PolicyError):
            await rt.create(
                policy_key=key,
                action_patterns=["*"],
                classification=ActionClassification.safe,
                risk_tier=RiskTier.standard,
            )

    async def test_supersede_increments_version(self, db: AsyncSession):
        rt = GovernancePolicyRuntime(db)
        key = f"p-{uuid4()}"
        await rt.create(
            policy_key=key,
            action_patterns=["workflow.*"],
            classification=ActionClassification.restricted,
            risk_tier=RiskTier.standard,
        )
        new_policy = await rt.supersede(
            key,
            action_patterns=["workflow.*"],
            classification=ActionClassification.privileged,
            risk_tier=RiskTier.high,
            routing_strategy=ApprovalRoutingStrategy.direct,
            approver_ids=[],
            escalation_chain=[],
            quorum_required=0,
            timeout_seconds=86400,
            escalation_timeout_seconds=3600,
            rules={},
        )
        assert new_policy.version == 2
        assert new_policy.status == GovernancePolicyStatus.active
        assert new_policy.classification == ActionClassification.privileged

    async def test_supersede_marks_old_superseded(self, db: AsyncSession):
        rt = GovernancePolicyRuntime(db)
        key = f"p-{uuid4()}"
        old = await rt.create(
            policy_key=key,
            action_patterns=["*"],
            classification=ActionClassification.safe,
            risk_tier=RiskTier.standard,
        )
        await rt.supersede(
            key,
            action_patterns=["*"],
            classification=ActionClassification.restricted,
            risk_tier=RiskTier.elevated,
            routing_strategy=ApprovalRoutingStrategy.direct,
            approver_ids=[],
            escalation_chain=[],
            quorum_required=0,
            timeout_seconds=86400,
            escalation_timeout_seconds=3600,
            rules={},
        )
        from sqlalchemy import select

        from models.governance_policy import GovernancePolicy
        result = await db.execute(select(GovernancePolicy).where(GovernancePolicy.id == old.id))
        refreshed = result.scalar_one()
        assert refreshed.status == GovernancePolicyStatus.superseded

    async def test_archive_policy(self, db: AsyncSession):
        rt = GovernancePolicyRuntime(db)
        key = f"p-{uuid4()}"
        await rt.create(
            policy_key=key,
            action_patterns=["*"],
            classification=ActionClassification.safe,
            risk_tier=RiskTier.standard,
        )
        archived = await rt.archive(key)
        assert archived.status == GovernancePolicyStatus.archived

    async def test_archive_missing_raises(self, db: AsyncSession):
        rt = GovernancePolicyRuntime(db)
        with pytest.raises(PolicyError):
            await rt.archive("nonexistent.policy")

    async def test_get_snapshot_returns_snapshot(self, db: AsyncSession):
        rt = GovernancePolicyRuntime(db)
        key = f"p-{uuid4()}"
        await rt.create(
            policy_key=key,
            action_patterns=["workflow.*"],
            classification=ActionClassification.restricted,
            risk_tier=RiskTier.elevated,
        )
        snap = await rt.get_snapshot(key)
        assert snap is not None
        assert snap.policy_key == key
        assert snap.version == 1

    async def test_get_snapshot_missing_returns_none(self, db: AsyncSession):
        rt = GovernancePolicyRuntime(db)
        snap = await rt.get_snapshot("never.created")
        assert snap is None

    async def test_get_all_snapshots_includes_new(self, db: AsyncSession):
        rt = GovernancePolicyRuntime(db)
        key = f"p-{uuid4()}"
        await rt.create(
            policy_key=key,
            action_patterns=["*"],
            classification=ActionClassification.safe,
            risk_tier=RiskTier.standard,
        )
        snapshots = await rt.get_all_snapshots()
        assert any(s.policy_key == key for s in snapshots)

    async def test_escalation_chain_stored_and_retrieved(self, db: AsyncSession):
        rt = GovernancePolicyRuntime(db)
        key = f"p-{uuid4()}"
        esc_id = uuid4()
        await rt.create(
            policy_key=key,
            action_patterns=["*"],
            classification=ActionClassification.restricted,
            risk_tier=RiskTier.elevated,
            escalation_chain=[{"escalate_to": str(esc_id), "after_seconds": 3600}],
        )
        snap = await rt.get_snapshot(key)
        assert len(snap.escalation_chain) == 1
        assert snap.escalation_chain[0].escalate_to == esc_id


# ---------------------------------------------------------------------------
# ApprovalRouter (DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestApprovalRouter:
    async def test_route_emits_event(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        ev = PolicyEvaluator()
        snap = _snapshot(
            action_patterns=("workflow.*",),
            classification=ActionClassification.restricted,
        )
        inp = PolicyEvaluationInput(action="workflow.outreach", risk_tier=RiskTier.standard)
        evaluation = ev.evaluate(inp, [snap])
        router = ApprovalRouter(db)
        route = await router.route(evaluation, approval.id)
        assert route.approval_id == approval.id
        events = await GovernanceEventRepository(db).get_for_approval(approval.id)
        assert any(e.event_type == GovernanceEventType.approval_routed for e in events)

    async def test_resolve_delegate_without_delegation_returns_actor(self, db: AsyncSession):
        router = ApprovalRouter(db)
        actor = uuid4()
        result = await router.resolve_delegate(actor, ApprovalType.outreach, RiskTier.standard)
        assert result == actor

    async def test_resolve_delegate_with_active_delegation(self, db: AsyncSession):
        delegator, delegate = uuid4(), uuid4()
        deleg_rt = DelegationRuntime(db)
        await deleg_rt.grant(
            delegation_key=f"d-{uuid4()}",
            delegator_id=delegator,
            delegate_id=delegate,
            approval_types=[ApprovalType.outreach],
            risk_tiers=[RiskTier.standard],
        )
        router = ApprovalRouter(db)
        effective = await router.resolve_delegate(delegate, ApprovalType.outreach, RiskTier.standard)
        assert effective == delegator

    async def test_resolve_delegate_scope_mismatch_returns_actor(self, db: AsyncSession):
        delegator, delegate = uuid4(), uuid4()
        deleg_rt = DelegationRuntime(db)
        await deleg_rt.grant(
            delegation_key=f"d-{uuid4()}",
            delegator_id=delegator,
            delegate_id=delegate,
            approval_types=[ApprovalType.offer],
        )
        router = ApprovalRouter(db)
        effective = await router.resolve_delegate(delegate, ApprovalType.outreach, RiskTier.standard)
        assert effective == delegate


# ---------------------------------------------------------------------------
# EscalationChainRuntime (DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestEscalationChainRuntime:
    async def test_escalate_updates_approval_status(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        rt = EscalationChainRuntime(db)
        step = EscalationStep(escalate_to=uuid4(), after_seconds=3600)
        await rt.escalate(approval.id, step, step_index=0)
        from repositories.approval import ApprovalRepository
        refreshed = await ApprovalRepository(db).get_by_id(approval.id)
        assert refreshed.approval_status == ApprovalStatus.escalated

    async def test_escalate_emits_event(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        rt = EscalationChainRuntime(db)
        step = EscalationStep(escalate_to=uuid4(), after_seconds=60)
        await rt.escalate(approval.id, step, step_index=0)
        events = await GovernanceEventRepository(db).get_for_approval(approval.id)
        assert any(e.event_type == GovernanceEventType.escalation_triggered for e in events)

    async def test_escalate_wrong_status_raises(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        approval.approval_status = ApprovalStatus.approved
        db.add(approval)
        await db.flush()
        rt = EscalationChainRuntime(db)
        step = EscalationStep(escalate_to=uuid4(), after_seconds=60)
        with pytest.raises(EscalationError):
            await rt.escalate(approval.id, step, step_index=0)

    async def test_escalate_missing_approval_raises(self, db: AsyncSession):
        rt = EscalationChainRuntime(db)
        step = EscalationStep(escalate_to=uuid4(), after_seconds=60)
        with pytest.raises(EscalationError):
            await rt.escalate(uuid4(), step, step_index=0)

    async def test_check_timeout_true_when_exceeded(self, db: AsyncSession):
        from governance.contracts import ApprovalRoute
        rt = EscalationChainRuntime(db)
        route = ApprovalRoute(
            approval_id=uuid4(),
            routing_strategy=ApprovalRoutingStrategy.direct,
            approver_ids=(),
            escalation_chain=(),
            quorum_required=0,
            timeout_seconds=1,
            escalation_timeout_seconds=1,
        )
        old_time = datetime.now(UTC) - timedelta(seconds=10)
        result = await rt.check_timeout(uuid4(), route, old_time)
        assert result is True

    async def test_check_timeout_false_when_within(self, db: AsyncSession):
        from governance.contracts import ApprovalRoute
        rt = EscalationChainRuntime(db)
        route = ApprovalRoute(
            approval_id=uuid4(),
            routing_strategy=ApprovalRoutingStrategy.direct,
            approver_ids=(),
            escalation_chain=(),
            quorum_required=0,
            timeout_seconds=9999,
            escalation_timeout_seconds=9999,
        )
        result = await rt.check_timeout(uuid4(), route, datetime.now(UTC))
        assert result is False

    async def test_get_current_step_counts_escalations(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        rt = EscalationChainRuntime(db)
        chain = (
            EscalationStep(escalate_to=uuid4(), after_seconds=60),
            EscalationStep(escalate_to=uuid4(), after_seconds=120),
        )
        await rt.escalate(approval.id, chain[0], step_index=0)
        step = await rt.get_current_step(approval.id, chain)
        assert step == 1

    async def test_get_current_step_zero_before_escalation(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        rt = EscalationChainRuntime(db)
        chain = (EscalationStep(escalate_to=uuid4(), after_seconds=60),)
        step = await rt.get_current_step(approval.id, chain)
        assert step == 0

    async def test_resolve_escalation_emits_event(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        rt = EscalationChainRuntime(db)
        await rt.resolve_escalation(approval.id)
        events = await GovernanceEventRepository(db).get_for_approval(approval.id)
        assert any(e.event_type == GovernanceEventType.escalation_resolved for e in events)


# ---------------------------------------------------------------------------
# QuorumRuntime (DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestQuorumRuntime:
    async def test_cast_vote_approve(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        rt = QuorumRuntime(db)
        result = await rt.cast_vote(approval.id, uuid4(), vote=True, required=2)
        assert result.votes_for == 1
        assert result.quorum_met is False

    async def test_quorum_met_on_enough_votes(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        rt = QuorumRuntime(db)
        await rt.cast_vote(approval.id, uuid4(), vote=True, required=2)
        result = await rt.cast_vote(approval.id, uuid4(), vote=True, required=2)
        assert result.quorum_met is True
        assert result.resolved is True

    async def test_duplicate_voter_raises(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        rt = QuorumRuntime(db)
        voter = uuid4()
        await rt.cast_vote(approval.id, voter, vote=True, required=3)
        with pytest.raises(QuorumError, match="already cast"):
            await rt.cast_vote(approval.id, voter, vote=True, required=3)

    async def test_vote_after_quorum_met_raises(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        rt = QuorumRuntime(db)
        await rt.cast_vote(approval.id, uuid4(), vote=True, required=2)
        await rt.cast_vote(approval.id, uuid4(), vote=True, required=2)
        with pytest.raises(QuorumError, match="already met"):
            await rt.cast_vote(approval.id, uuid4(), vote=True, required=2)

    async def test_get_result_counts_votes(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        rt = QuorumRuntime(db)
        await rt.cast_vote(approval.id, uuid4(), vote=True, required=3)
        await rt.cast_vote(approval.id, uuid4(), vote=False, required=3)
        result = await rt.get_result(approval.id, required=3)
        assert result.votes_for == 1
        assert result.votes_against == 1
        assert result.quorum_met is False

    async def test_quorum_met_emits_event(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        rt = QuorumRuntime(db)
        await rt.cast_vote(approval.id, uuid4(), vote=True, required=1)
        events = await GovernanceEventRepository(db).get_for_approval(approval.id)
        assert any(e.event_type == GovernanceEventType.quorum_met for e in events)

    async def test_build_vote_does_not_persist(self, db: AsyncSession):
        rt = QuorumRuntime(db)
        vote = rt.build_vote(uuid4(), uuid4(), vote=True)
        assert vote.vote is True


# ---------------------------------------------------------------------------
# DelegationRuntime (DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestDelegationRuntime:
    async def test_grant_creates_delegation(self, db: AsyncSession):
        rt = DelegationRuntime(db)
        delegator, delegate = uuid4(), uuid4()
        grant = await rt.grant(
            delegation_key=f"d-{uuid4()}",
            delegator_id=delegator,
            delegate_id=delegate,
        )
        assert grant.delegation_id is not None
        assert grant.delegator_id == delegator
        assert grant.delegate_id == delegate

    async def test_grant_idempotent(self, db: AsyncSession):
        rt = DelegationRuntime(db)
        key = f"d-{uuid4()}"
        delegator, delegate = uuid4(), uuid4()
        g1 = await rt.grant(delegation_key=key, delegator_id=delegator, delegate_id=delegate)
        g2 = await rt.grant(delegation_key=key, delegator_id=delegator, delegate_id=delegate)
        assert g1.delegation_id == g2.delegation_id

    async def test_revoke_sets_revoked_status(self, db: AsyncSession):
        rt = DelegationRuntime(db)
        key = f"d-{uuid4()}"
        await rt.grant(delegation_key=key, delegator_id=uuid4(), delegate_id=uuid4())
        delegation = await rt.revoke(key, revoke_reason="test revoke")
        from models.enums import DelegationStatus
        assert delegation.status == DelegationStatus.revoked
        assert delegation.revoke_reason == "test revoke"

    async def test_revoke_missing_raises(self, db: AsyncSession):
        rt = DelegationRuntime(db)
        with pytest.raises(DelegationError):
            await rt.revoke("nonexistent-key")

    async def test_revoke_already_revoked_raises(self, db: AsyncSession):
        rt = DelegationRuntime(db)
        key = f"d-{uuid4()}"
        await rt.grant(delegation_key=key, delegator_id=uuid4(), delegate_id=uuid4())
        await rt.revoke(key)
        with pytest.raises(DelegationError):
            await rt.revoke(key)

    async def test_is_authorized_with_active_delegation(self, db: AsyncSession):
        rt = DelegationRuntime(db)
        delegate = uuid4()
        await rt.grant(
            delegation_key=f"d-{uuid4()}",
            delegator_id=uuid4(),
            delegate_id=delegate,
            approval_types=[ApprovalType.outreach],
            risk_tiers=[RiskTier.standard],
        )
        authorized = await rt.is_authorized(delegate, ApprovalType.outreach, RiskTier.standard)
        assert authorized is True

    async def test_is_authorized_scope_mismatch(self, db: AsyncSession):
        rt = DelegationRuntime(db)
        delegate = uuid4()
        await rt.grant(
            delegation_key=f"d-{uuid4()}",
            delegator_id=uuid4(),
            delegate_id=delegate,
            approval_types=[ApprovalType.offer],
        )
        authorized = await rt.is_authorized(delegate, ApprovalType.outreach, RiskTier.standard)
        assert authorized is False

    async def test_is_authorized_no_delegation(self, db: AsyncSession):
        rt = DelegationRuntime(db)
        authorized = await rt.is_authorized(uuid4(), ApprovalType.outreach, RiskTier.standard)
        assert authorized is False

    async def test_is_authorized_broad_delegation(self, db: AsyncSession):
        rt = DelegationRuntime(db)
        delegate = uuid4()
        await rt.grant(
            delegation_key=f"d-{uuid4()}",
            delegator_id=uuid4(),
            delegate_id=delegate,
            approval_types=[],
            risk_tiers=[],
        )
        for apt in [ApprovalType.offer, ApprovalType.outreach, ApprovalType.skip_trace]:
            assert await rt.is_authorized(delegate, apt, RiskTier.critical) is True

    async def test_grant_emits_governance_event(self, db: AsyncSession):
        rt = DelegationRuntime(db)
        key = f"d-{uuid4()}"
        await rt.grant(delegation_key=key, delegator_id=uuid4(), delegate_id=uuid4())
        events = await GovernanceEventRepository(db).get_by_type(
            GovernanceEventType.delegation_granted
        )
        assert any(e.payload.get("delegation_key") == key for e in events)


# ---------------------------------------------------------------------------
# FreezeRuntime (DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestFreezeRuntime:
    async def test_activate_and_is_frozen(self, db: AsyncSession):
        rt = FreezeRuntime(db)
        scope = f"global-{uuid4()}"
        await rt.activate(f"fk-{uuid4()}", scope, reason="test freeze")
        assert await rt.is_frozen(scope) is True

    async def test_is_frozen_false_when_not_frozen(self, db: AsyncSession):
        rt = FreezeRuntime(db)
        assert await rt.is_frozen(f"never-frozen-{uuid4()}") is False

    async def test_deactivate_clears_freeze(self, db: AsyncSession):
        rt = FreezeRuntime(db)
        scope = f"scope-{uuid4()}"
        fk = f"fk-{uuid4()}"
        await rt.activate(fk, scope, reason="x")
        await rt.deactivate(fk)
        assert await rt.is_frozen(scope) is False

    async def test_kill_switch_permanent(self, db: AsyncSession):
        rt = FreezeRuntime(db)
        scope = f"scope-{uuid4()}"
        await rt.kill_switch(f"ks-{uuid4()}", scope, reason="emergency")
        assert await rt.is_frozen(scope) is True

    async def test_kill_switch_scope_stays_frozen_after_deactivating_regular_freeze(self, db: AsyncSession):
        rt = FreezeRuntime(db)
        scope = f"scope-{uuid4()}"
        # Activate regular freeze first
        fk_regular = f"fk-regular-{uuid4()}"
        await rt.activate(fk_regular, scope, reason="regular")
        # Add kill switch
        await rt.kill_switch(f"ks-{uuid4()}", scope, reason="permanent")
        # Deactivate regular freeze
        await rt.deactivate(fk_regular)
        # Kill switch still keeps scope frozen
        assert await rt.is_frozen(scope) is True

    async def test_activate_returns_freeze_spec(self, db: AsyncSession):
        rt = FreezeRuntime(db)
        scope = f"scope-{uuid4()}"
        spec = await rt.activate(f"fk-{uuid4()}", scope, reason="test")
        assert spec.scope == scope
        assert spec.is_kill_switch is False

    async def test_kill_switch_returns_freeze_spec(self, db: AsyncSession):
        rt = FreezeRuntime(db)
        scope = f"scope-{uuid4()}"
        spec = await rt.kill_switch(f"ks-{uuid4()}", scope, reason="halt")
        assert spec.is_kill_switch is True


# ---------------------------------------------------------------------------
# EmergencyOverrideRuntime (DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestEmergencyOverrideRuntime:
    async def test_apply_resolves_approval(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        rt = EmergencyOverrideRuntime(db)
        override = await rt.apply(
            override_key=f"ov-{uuid4()}",
            approval_id=approval.id,
            authorized_by=uuid4(),
            reason="emergency bypass",
        )
        assert override.approval_id == approval.id
        from repositories.approval import ApprovalRepository
        refreshed = await ApprovalRepository(db).get_by_id(approval.id)
        assert refreshed.approval_status == ApprovalStatus.approved

    async def test_apply_idempotent(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        rt = EmergencyOverrideRuntime(db)
        key = f"ov-{uuid4()}"
        auth = uuid4()
        o1 = await rt.apply(key, approval.id, auth, reason="first")
        o2 = await rt.apply(key, approval.id, auth, reason="second")
        assert o1.override_id == o2.override_id

    async def test_apply_already_resolved_raises(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        approval.approval_status = ApprovalStatus.approved
        db.add(approval)
        await db.flush()
        rt = EmergencyOverrideRuntime(db)
        with pytest.raises(OverrideError):
            await rt.apply(f"ov-{uuid4()}", approval.id, uuid4(), reason="too late")

    async def test_apply_emits_mandatory_audit(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        rt = EmergencyOverrideRuntime(db)
        await rt.apply(f"ov-{uuid4()}", approval.id, uuid4(), reason="audit test")
        events = await GovernanceEventRepository(db).get_for_approval(approval.id)
        assert any(e.event_type == GovernanceEventType.override_applied for e in events)

    async def test_apply_missing_approval_raises(self, db: AsyncSession):
        rt = EmergencyOverrideRuntime(db)
        with pytest.raises(OverrideError):
            await rt.apply(f"ov-{uuid4()}", uuid4(), uuid4(), reason="no approval")

    async def test_apply_sets_resolution_notes(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        rt = EmergencyOverrideRuntime(db)
        await rt.apply(f"ov-{uuid4()}", approval.id, uuid4(), reason="my reason")
        from repositories.approval import ApprovalRepository
        refreshed = await ApprovalRepository(db).get_by_id(approval.id)
        assert "my reason" in refreshed.resolution_notes


# ---------------------------------------------------------------------------
# GovernanceAuditRuntime (DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGovernanceAuditRuntime:
    async def test_record_and_retrieve(self, db: AsyncSession):
        rt = GovernanceAuditRuntime(db)
        target = uuid4()
        entry = await rt.record(
            action=ACTION_POLICY_EVALUATED,
            target_id=target,
            payload={"action": "workflow.test"},
        )
        assert entry.entry_id is not None
        assert entry.action == ACTION_POLICY_EVALUATED

    async def test_get_for_target_ordered(self, db: AsyncSession):
        rt = GovernanceAuditRuntime(db)
        target = uuid4()
        await rt.record(action="gov_event_1", target_id=target)
        await rt.record(action="gov_event_2", target_id=target)
        entries = await rt.get_for_target(target)
        actions = [e.action for e in entries]
        assert "gov_event_1" in actions
        assert "gov_event_2" in actions

    async def test_get_for_target_empty(self, db: AsyncSession):
        rt = GovernanceAuditRuntime(db)
        entries = await rt.get_for_target(uuid4())
        assert entries == []

    async def test_record_no_target(self, db: AsyncSession):
        rt = GovernanceAuditRuntime(db)
        entry = await rt.record(action="gov_misc_event", payload={"key": "val"})
        assert entry.target_id is None


# ---------------------------------------------------------------------------
# GovernancePolicySnapshotRuntime (DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGovernancePolicySnapshotRuntime:
    async def test_capture_creates_snapshot(self, db: AsyncSession):
        pol_rt = GovernancePolicyRuntime(db)
        key = f"p-{uuid4()}"
        await pol_rt.create(
            policy_key=key,
            action_patterns=["workflow.*"],
            classification=ActionClassification.restricted,
            risk_tier=RiskTier.elevated,
        )
        snap_rt = GovernancePolicySnapshotRuntime(db)
        snap = await snap_rt.capture(key)
        assert snap.policy_key == key
        assert snap.version == 1
        assert snap.classification == ActionClassification.restricted

    async def test_capture_missing_raises(self, db: AsyncSession):
        snap_rt = GovernancePolicySnapshotRuntime(db)
        with pytest.raises(SnapshotError):
            await snap_rt.capture("nonexistent.policy")

    async def test_replay_snapshots_reconstructs(self, db: AsyncSession):
        pol_rt = GovernancePolicyRuntime(db)
        key = f"p-{uuid4()}"
        policy = await pol_rt.create(
            policy_key=key,
            action_patterns=["ai.*"],
            classification=ActionClassification.privileged,
            risk_tier=RiskTier.high,
        )
        snap_rt = GovernancePolicySnapshotRuntime(db)
        await snap_rt.capture(key)
        snapshots = await snap_rt.replay_snapshots(policy.id)
        assert len(snapshots) >= 1
        assert snapshots[-1].policy_key == key

    async def test_capture_persists_escalation_chain(self, db: AsyncSession):
        pol_rt = GovernancePolicyRuntime(db)
        key = f"p-{uuid4()}"
        esc_id = uuid4()
        await pol_rt.create(
            policy_key=key,
            action_patterns=["*"],
            classification=ActionClassification.restricted,
            risk_tier=RiskTier.elevated,
            escalation_chain=[{"escalate_to": str(esc_id), "after_seconds": 3600}],
        )
        snap_rt = GovernancePolicySnapshotRuntime(db)
        snap = await snap_rt.capture(key)
        assert len(snap.escalation_chain) == 1
        assert snap.escalation_chain[0].escalate_to == esc_id

    async def test_capture_persists_governance_event(self, db: AsyncSession):
        pol_rt = GovernancePolicyRuntime(db)
        key = f"p-{uuid4()}"
        policy = await pol_rt.create(
            policy_key=key,
            action_patterns=["*"],
            classification=ActionClassification.safe,
            risk_tier=RiskTier.standard,
        )
        snap_rt = GovernancePolicySnapshotRuntime(db)
        await snap_rt.capture(key)
        events = await GovernanceEventRepository(db).get_for_policy(policy.id)
        # Policy creation also emits a snapshot event, plus capture adds another
        snap_events = [e for e in events if e.event_type == GovernanceEventType.policy_snapshot_captured]
        assert len(snap_events) >= 1


# ---------------------------------------------------------------------------
# GovernanceMetricsRuntime (DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGovernanceMetricsRuntime:
    async def test_compute_returns_metrics(self, db: AsyncSession):
        rt = GovernanceMetricsRuntime(db)
        now = datetime.now(UTC)
        start = now - timedelta(hours=1)
        metrics = await rt.compute(start, now)
        assert isinstance(metrics.total_evaluations, int)
        assert isinstance(metrics.approvals_pending, int)
        assert metrics.period_start == start
        assert metrics.period_end == now

    async def test_compute_counts_pending_approvals(self, db: AsyncSession):
        wf = await _make_workflow(db)
        await _make_approval(db, wf.id)
        rt = GovernanceMetricsRuntime(db)
        now = datetime.now(UTC)
        start = now - timedelta(hours=1)
        metrics = await rt.compute(start, now)
        assert metrics.approvals_pending >= 1

    async def test_compute_counts_delegations(self, db: AsyncSession):
        deleg_rt = DelegationRuntime(db)
        await deleg_rt.grant(
            delegation_key=f"d-metrics-{uuid4()}",
            delegator_id=uuid4(),
            delegate_id=uuid4(),
        )
        rt = GovernanceMetricsRuntime(db)
        now = datetime.now(UTC)
        metrics = await rt.compute(now - timedelta(hours=1), now)
        assert metrics.delegations_active >= 1

    async def test_compute_counts_overrides(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        ov_rt = EmergencyOverrideRuntime(db)
        await ov_rt.apply(f"ov-{uuid4()}", approval.id, uuid4(), reason="metrics test")
        rt = GovernanceMetricsRuntime(db)
        now = datetime.now(UTC)
        metrics = await rt.compute(now - timedelta(hours=1), now)
        assert metrics.overrides_applied >= 1


# ---------------------------------------------------------------------------
# ApprovalHistoryReconstructor (DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestApprovalHistoryReconstructor:
    async def test_reconstruct_returns_history(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        ev_repo = GovernanceEventRepository(db)
        await ev_repo.append(
            event_type=GovernanceEventType.approval_routed,
            approval_id=approval.id,
            payload={"routing_strategy": "direct"},
        )
        rt = ApprovalHistoryReconstructor(db)
        history = await rt.reconstruct(approval.id)
        assert history is not None
        assert history.approval_id == approval.id
        assert len(history.entries) == 1
        assert history.fully_reconstructed is True

    async def test_reconstruct_counts_escalations(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        esc_rt = EscalationChainRuntime(db)
        step = EscalationStep(escalate_to=uuid4(), after_seconds=60)
        await esc_rt.escalate(approval.id, step, step_index=0)
        rt = ApprovalHistoryReconstructor(db)
        history = await rt.reconstruct(approval.id)
        assert history.escalation_depth == 1

    async def test_reconstruct_detects_override(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        ov_rt = EmergencyOverrideRuntime(db)
        await ov_rt.apply(f"ov-{uuid4()}", approval.id, uuid4(), reason="test")
        rt = ApprovalHistoryReconstructor(db)
        history = await rt.reconstruct(approval.id)
        assert history.override_applied is True

    async def test_reconstruct_missing_approval_returns_none(self, db: AsyncSession):
        rt = ApprovalHistoryReconstructor(db)
        history = await rt.reconstruct(uuid4())
        assert history is None

    async def test_reconstruct_counts_quorum_votes(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        q_rt = QuorumRuntime(db)
        await q_rt.cast_vote(approval.id, uuid4(), vote=True, required=5)
        await q_rt.cast_vote(approval.id, uuid4(), vote=False, required=5)
        rt = ApprovalHistoryReconstructor(db)
        history = await rt.reconstruct(approval.id)
        assert history.quorum_votes == 2

    async def test_reconstruct_empty_approval(self, db: AsyncSession):
        wf = await _make_workflow(db)
        approval = await _make_approval(db, wf.id)
        rt = ApprovalHistoryReconstructor(db)
        history = await rt.reconstruct(approval.id)
        assert history is not None
        assert len(history.entries) == 0
        assert history.override_applied is False


# ---------------------------------------------------------------------------
# Repository layer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGovernancePolicyRepository:
    async def test_get_active(self, db: AsyncSession):
        rt = GovernancePolicyRuntime(db)
        key = f"p-{uuid4()}"
        await rt.create(
            policy_key=key,
            action_patterns=["*"],
            classification=ActionClassification.safe,
            risk_tier=RiskTier.standard,
        )
        repo = GovernancePolicyRepository(db)
        active = await repo.get_active()
        assert any(p.policy_key == key for p in active)

    async def test_get_active_version(self, db: AsyncSession):
        rt = GovernancePolicyRuntime(db)
        key = f"p-{uuid4()}"
        await rt.create(
            policy_key=key,
            action_patterns=["*"],
            classification=ActionClassification.safe,
            risk_tier=RiskTier.standard,
        )
        repo = GovernancePolicyRepository(db)
        pol = await repo.get_active_version(key)
        assert pol is not None
        assert pol.status == GovernancePolicyStatus.active

    async def test_get_latest_version_number_zero_for_new(self, db: AsyncSession):
        repo = GovernancePolicyRepository(db)
        n = await repo.get_latest_version_number(f"never-existed-{uuid4()}")
        assert n == 0

    async def test_get_by_key_returns_all_versions(self, db: AsyncSession):
        rt = GovernancePolicyRuntime(db)
        key = f"p-{uuid4()}"
        await rt.create(
            policy_key=key,
            action_patterns=["*"],
            classification=ActionClassification.safe,
            risk_tier=RiskTier.standard,
        )
        await rt.supersede(
            key,
            action_patterns=["*"],
            classification=ActionClassification.restricted,
            risk_tier=RiskTier.elevated,
            routing_strategy=ApprovalRoutingStrategy.direct,
            approver_ids=[],
            escalation_chain=[],
            quorum_required=0,
            timeout_seconds=86400,
            escalation_timeout_seconds=3600,
            rules={},
        )
        repo = GovernancePolicyRepository(db)
        versions = await repo.get_by_key(key)
        assert len(versions) == 2


@pytest.mark.asyncio
class TestGovernanceEventRepository:
    async def test_append_and_get_for_approval(self, db: AsyncSession):
        repo = GovernanceEventRepository(db)
        appr_id = uuid4()
        evt = await repo.append(
            event_type=GovernanceEventType.approval_routed,
            approval_id=appr_id,
            payload={"test": True},
        )
        assert evt.id is not None
        events = await repo.get_for_approval(appr_id)
        assert len(events) == 1

    async def test_get_by_type(self, db: AsyncSession):
        repo = GovernanceEventRepository(db)
        await repo.append(
            event_type=GovernanceEventType.policy_evaluated,
            payload={"action": "test"},
        )
        events = await repo.get_by_type(GovernanceEventType.policy_evaluated)
        assert len(events) >= 1

    async def test_get_for_policy(self, db: AsyncSession):
        repo = GovernanceEventRepository(db)
        policy_id = uuid4()
        await repo.append(
            event_type=GovernanceEventType.policy_snapshot_captured,
            policy_id=policy_id,
            payload={},
        )
        events = await repo.get_for_policy(policy_id)
        assert len(events) == 1


@pytest.mark.asyncio
class TestApprovalDelegationRepository:
    async def test_get_by_key(self, db: AsyncSession):
        rt = DelegationRuntime(db)
        key = f"d-{uuid4()}"
        grant = await rt.grant(
            delegation_key=key,
            delegator_id=uuid4(),
            delegate_id=uuid4(),
        )
        repo = ApprovalDelegationRepository(db)
        found = await repo.get_by_key(key)
        assert found is not None
        assert found.id == grant.delegation_id

    async def test_get_active_for_delegate(self, db: AsyncSession):
        rt = DelegationRuntime(db)
        delegate = uuid4()
        await rt.grant(f"d-{uuid4()}", uuid4(), delegate)
        repo = ApprovalDelegationRepository(db)
        delegations = await repo.get_active_for_delegate(delegate)
        assert len(delegations) >= 1

    async def test_get_active_for_delegator(self, db: AsyncSession):
        rt = DelegationRuntime(db)
        delegator = uuid4()
        await rt.grant(f"d-{uuid4()}", delegator, uuid4())
        repo = ApprovalDelegationRepository(db)
        delegations = await repo.get_active_for_delegator(delegator)
        assert len(delegations) >= 1
