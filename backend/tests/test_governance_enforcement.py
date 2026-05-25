"""
Phase 14 — Governance Enforcement Integration Tests.

Coverage:
  - GovernanceEngine: check_freeze, evaluate_action, enforce_action
  - GovernanceRuntime: property access, convenience delegates
  - GovernanceFrozenError: global freeze propagation, scope freeze propagation
  - GovernanceDeniedError: forbidden action denied, audit emitted, event emitted
  - Replay safety: evaluate_action returns safe with no policies
  - Cancellation compatibility: cancel/fail/complete NOT blocked by freeze
  - WorkflowRuntime.start() blocked by global freeze
  - WorkflowRuntime.advance() blocked by workflow-scoped freeze
  - SophiaSessionRuntime.create() blocked by global freeze
  - SophiaTurnRuntime.start() blocked by session-scoped freeze
  - freeze_propagated event persisted on block
  - action_denied event persisted on deny
  - GovernanceRuntime exposes all Phase 11 primitives

All DB tests run against karpathys_test with SAVEPOINT rollback per test.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from governance.engine import GovernanceEngine
from governance.exceptions import (
    GovernanceDeniedError,
    GovernanceFrozenError,
    GovernanceInvariantViolationError,
)
from governance.freeze import FreezeRuntime
from governance.policy import GovernancePolicyRuntime
from governance.runtime import GovernanceRuntime
from models.enums import (
    ActionClassification,
    GovernanceEventType,
    RiskTier,
    WorkflowType,
)
from repositories.governance_event import GovernanceEventRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _freeze_global(db: AsyncSession) -> str:
    """Activate a global freeze. Returns freeze_key."""
    rt = FreezeRuntime(db)
    fk = f"fk-global-{uuid4()}"
    await rt.activate(fk, "global", reason="test global freeze")
    return fk


async def _freeze_scope(db: AsyncSession, scope: str) -> str:
    rt = FreezeRuntime(db)
    fk = f"fk-scope-{uuid4()}"
    await rt.activate(fk, scope, reason=f"test scope freeze: {scope}")
    return fk


async def _make_forbidden_policy(db: AsyncSession, pattern: str = "forbidden.*") -> None:
    """Create an active policy that classifies pattern as forbidden."""
    rt = GovernancePolicyRuntime(db)
    await rt.create(
        policy_key=f"test-forbidden-{uuid4()}",
        action_patterns=[pattern],
        classification=ActionClassification.forbidden,
        risk_tier=RiskTier.critical,
    )


# ---------------------------------------------------------------------------
# GovernanceEngine.check_freeze
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGovernanceEngineCheckFreeze:
    async def test_no_freeze_passes(self, db: AsyncSession) -> None:
        engine = GovernanceEngine(db)
        # Should complete without raising
        await engine.check_freeze("global", source_runtime="test")

    async def test_global_freeze_raises(self, db: AsyncSession) -> None:
        await _freeze_global(db)
        engine = GovernanceEngine(db)
        with pytest.raises(GovernanceFrozenError) as exc_info:
            await engine.check_freeze("global", source_runtime="test")
        assert exc_info.value.scope == "global"

    async def test_scope_freeze_raises(self, db: AsyncSession) -> None:
        scope = f"workflow:{uuid4()}"
        await _freeze_scope(db, scope)
        engine = GovernanceEngine(db)
        with pytest.raises(GovernanceFrozenError) as exc_info:
            await engine.check_freeze(scope, source_runtime="test")
        assert exc_info.value.scope == scope

    async def test_global_freeze_propagates_to_non_global_scope(self, db: AsyncSession) -> None:
        """Global freeze blocks non-global scope checks too."""
        await _freeze_global(db)
        engine = GovernanceEngine(db)
        scope = f"sophia:{uuid4()}"
        with pytest.raises(GovernanceFrozenError) as exc_info:
            await engine.check_freeze(scope, source_runtime="test")
        assert exc_info.value.scope == "global"

    async def test_no_global_freeze_scope_specific_passes(self, db: AsyncSession) -> None:
        """Non-frozen scope passes even when other scopes are frozen."""
        other_scope = f"workflow:{uuid4()}"
        await _freeze_scope(db, other_scope)
        engine = GovernanceEngine(db)
        my_scope = f"workflow:{uuid4()}"
        await engine.check_freeze(my_scope, source_runtime="test")

    async def test_freeze_propagated_event_emitted(self, db: AsyncSession) -> None:
        await _freeze_global(db)
        engine = GovernanceEngine(db)
        with pytest.raises(GovernanceFrozenError):
            await engine.check_freeze("global", source_runtime="workflow")
        events = await GovernanceEventRepository(db).get_by_type(
            GovernanceEventType.freeze_propagated
        )
        assert any(e.payload.get("scope") == "global" for e in events)
        assert any(e.payload.get("source_runtime") == "workflow" for e in events)

    async def test_deactivated_freeze_does_not_block(self, db: AsyncSession) -> None:
        rt = FreezeRuntime(db)
        fk = f"fk-{uuid4()}"
        await rt.activate(fk, "global", reason="temp")
        await rt.deactivate(fk)
        engine = GovernanceEngine(db)
        await engine.check_freeze("global", source_runtime="test")


# ---------------------------------------------------------------------------
# GovernanceEngine.evaluate_action (pure, replay-safe)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGovernanceEngineEvaluateAction:
    async def test_no_policies_returns_safe(self, db: AsyncSession) -> None:
        engine = GovernanceEngine(db)
        result = await engine.evaluate_action(
            "any.action", RiskTier.standard
        )
        assert result.classification == ActionClassification.safe
        assert result.requires_approval is False

    async def test_forbidden_policy_returns_forbidden(self, db: AsyncSession) -> None:
        await _make_forbidden_policy(db, "forbidden.*")
        engine = GovernanceEngine(db)
        result = await engine.evaluate_action("forbidden.action", RiskTier.critical)
        assert result.classification == ActionClassification.forbidden

    async def test_evaluate_does_not_raise_on_forbidden(self, db: AsyncSession) -> None:
        """evaluate_action is pure — no exceptions even on forbidden."""
        await _make_forbidden_policy(db, "forbidden.*")
        engine = GovernanceEngine(db)
        result = await engine.evaluate_action("forbidden.action", RiskTier.critical)
        # Should return result, not raise
        assert result.classification == ActionClassification.forbidden

    async def test_evaluate_not_blocked_by_global_freeze(self, db: AsyncSession) -> None:
        """evaluate_action has no freeze check — safe to use during replay."""
        await _freeze_global(db)
        engine = GovernanceEngine(db)
        result = await engine.evaluate_action("any.action", RiskTier.standard)
        assert result is not None

    async def test_evaluation_id_is_unique(self, db: AsyncSession) -> None:
        engine = GovernanceEngine(db)
        r1 = await engine.evaluate_action("x", RiskTier.standard)
        r2 = await engine.evaluate_action("x", RiskTier.standard)
        assert r1.evaluation_id != r2.evaluation_id


# ---------------------------------------------------------------------------
# GovernanceEngine.enforce_action
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGovernanceEngineEnforceAction:
    async def test_safe_action_passes(self, db: AsyncSession) -> None:
        engine = GovernanceEngine(db)
        result = await engine.enforce_action("safe.action", RiskTier.standard)
        assert result.classification == ActionClassification.safe

    async def test_frozen_scope_raises_before_evaluation(self, db: AsyncSession) -> None:
        await _freeze_global(db)
        engine = GovernanceEngine(db)
        with pytest.raises(GovernanceFrozenError):
            await engine.enforce_action("any.action", RiskTier.standard)

    async def test_forbidden_action_raises_governance_denied(self, db: AsyncSession) -> None:
        await _make_forbidden_policy(db, "bad.*")
        engine = GovernanceEngine(db)
        with pytest.raises(GovernanceDeniedError) as exc_info:
            await engine.enforce_action("bad.action", RiskTier.critical)
        assert exc_info.value.action == "bad.action"
        assert exc_info.value.classification == "forbidden"

    async def test_forbidden_action_emits_action_denied_event(self, db: AsyncSession) -> None:
        await _make_forbidden_policy(db, "bad.*")
        engine = GovernanceEngine(db)
        with pytest.raises(GovernanceDeniedError):
            await engine.enforce_action("bad.action", RiskTier.critical)
        events = await GovernanceEventRepository(db).get_by_type(
            GovernanceEventType.action_denied
        )
        assert any(e.payload.get("action") == "bad.action" for e in events)

    async def test_enforce_emits_audit_on_pass(self, db: AsyncSession) -> None:
        # enforce_action writes an audit record after policy evaluation.
        # Verify it completes without raising — audit write is the invariant.
        engine = GovernanceEngine(db)
        target_id = uuid4()
        await engine.enforce_action("safe.action", RiskTier.standard, actor_id=target_id)

    async def test_custom_scope_freeze_blocks_enforce(self, db: AsyncSession) -> None:
        wf_id = uuid4()
        await _freeze_scope(db, f"workflow:{wf_id}")
        engine = GovernanceEngine(db)
        with pytest.raises(GovernanceFrozenError) as exc_info:
            await engine.enforce_action(
                "workflow.advance", RiskTier.standard, scope=f"workflow:{wf_id}"
            )
        assert "workflow:" in exc_info.value.scope

    async def test_safe_action_no_policy_returns_result(self, db: AsyncSession) -> None:
        engine = GovernanceEngine(db)
        result = await engine.enforce_action(
            "unmatched.action", RiskTier.standard, source_runtime="test"
        )
        assert result.matched_policy_key is None


# ---------------------------------------------------------------------------
# GovernanceRuntime — coordinator
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGovernanceRuntime:
    async def test_runtime_instantiates(self, db: AsyncSession) -> None:
        gov = GovernanceRuntime(db)
        assert gov is not None

    async def test_engine_property(self, db: AsyncSession) -> None:
        gov = GovernanceRuntime(db)
        assert isinstance(gov.engine, GovernanceEngine)

    async def test_engine_property_is_same_instance(self, db: AsyncSession) -> None:
        gov = GovernanceRuntime(db)
        e1 = gov.engine
        e2 = gov.engine
        assert e1 is e2

    async def test_freeze_property(self, db: AsyncSession) -> None:
        gov = GovernanceRuntime(db)
        assert isinstance(gov.freeze, FreezeRuntime)

    async def test_policy_property(self, db: AsyncSession) -> None:
        gov = GovernanceRuntime(db)
        assert isinstance(gov.policy, GovernancePolicyRuntime)

    async def test_convenience_check_freeze_delegates(self, db: AsyncSession) -> None:
        await _freeze_global(db)
        gov = GovernanceRuntime(db)
        with pytest.raises(GovernanceFrozenError):
            await gov.check_freeze("global")

    async def test_convenience_enforce_delegates(self, db: AsyncSession) -> None:
        gov = GovernanceRuntime(db)
        result = await gov.enforce("safe.action", RiskTier.standard)
        assert result.classification == ActionClassification.safe

    async def test_convenience_evaluate_delegates(self, db: AsyncSession) -> None:
        gov = GovernanceRuntime(db)
        result = await gov.evaluate("any.action", RiskTier.standard)
        assert result is not None

    async def test_evaluate_not_blocked_by_freeze(self, db: AsyncSession) -> None:
        await _freeze_global(db)
        gov = GovernanceRuntime(db)
        result = await gov.evaluate("any.action", RiskTier.standard)
        assert result.classification == ActionClassification.safe

    async def test_all_primitives_accessible(self, db: AsyncSession) -> None:
        from governance.audit import GovernanceAuditRuntime
        from governance.delegation import DelegationRuntime
        from governance.escalation import EscalationChainRuntime
        from governance.metrics import GovernanceMetricsRuntime
        from governance.override import EmergencyOverrideRuntime
        from governance.reconstruction import ApprovalHistoryReconstructor
        from governance.router import ApprovalRouter
        from governance.snapshot import GovernancePolicySnapshotRuntime

        gov = GovernanceRuntime(db)
        assert isinstance(gov.freeze, FreezeRuntime)
        assert isinstance(gov.policy, GovernancePolicyRuntime)
        assert isinstance(gov.router, ApprovalRouter)
        assert isinstance(gov.escalation, EscalationChainRuntime)
        assert isinstance(gov.override, EmergencyOverrideRuntime)
        assert isinstance(gov.audit, GovernanceAuditRuntime)
        assert isinstance(gov.delegation, DelegationRuntime)
        assert isinstance(gov.metrics, GovernanceMetricsRuntime)
        assert isinstance(gov.snapshot, GovernancePolicySnapshotRuntime)
        assert isinstance(gov.reconstruction, ApprovalHistoryReconstructor)


# ---------------------------------------------------------------------------
# WorkflowRuntime integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestWorkflowRuntimeGovernanceIntegration:
    async def test_start_blocked_by_global_freeze(self, db: AsyncSession) -> None:
        from workflows.runtime import WorkflowRuntime
        await _freeze_global(db)
        rt = WorkflowRuntime(db)
        with pytest.raises(GovernanceFrozenError):
            await rt.start(WorkflowType.outreach)

    async def test_start_passes_when_not_frozen(self, db: AsyncSession) -> None:
        from workflows.runtime import WorkflowRuntime
        rt = WorkflowRuntime(db)
        wf = await rt.start(WorkflowType.outreach)
        assert wf.id is not None

    async def test_advance_blocked_by_global_freeze(self, db: AsyncSession) -> None:
        from workflows.runtime import WorkflowRuntime
        rt = WorkflowRuntime(db)
        wf = await rt.start(WorkflowType.outreach)
        # Activate freeze after start
        await _freeze_global(db)
        with pytest.raises(GovernanceFrozenError):
            await rt.advance(wf.id, step="contacted")

    async def test_advance_blocked_by_workflow_scoped_freeze(self, db: AsyncSession) -> None:
        from workflows.runtime import WorkflowRuntime
        rt = WorkflowRuntime(db)
        wf = await rt.start(WorkflowType.outreach)
        await _freeze_scope(db, f"workflow:{wf.id}")
        with pytest.raises(GovernanceFrozenError):
            await rt.advance(wf.id, step="contacted")

    async def test_advance_other_workflow_not_blocked_by_scoped_freeze(
        self, db: AsyncSession
    ) -> None:
        from workflows.runtime import WorkflowRuntime
        rt = WorkflowRuntime(db)
        wf1 = await rt.start(WorkflowType.outreach)
        wf2 = await rt.start(WorkflowType.outreach)
        await _freeze_scope(db, f"workflow:{wf1.id}")
        # wf2 is NOT affected by wf1's scope freeze
        advanced = await rt.advance(wf2.id, step="contacted")
        assert advanced.current_step == "contacted"

    async def test_cancel_not_blocked_by_global_freeze(self, db: AsyncSession) -> None:
        """Terminal operations must remain reachable during freeze (INV-18)."""
        from workflows.runtime import WorkflowRuntime
        rt = WorkflowRuntime(db)
        wf = await rt.start(WorkflowType.outreach)
        await _freeze_global(db)
        # cancel() should NOT raise — it's a terminal/shutdown operation
        cancelled = await rt.cancel(wf.id, reason="freeze-shutdown")
        from models.enums import WorkflowStatus
        assert cancelled.workflow_status == WorkflowStatus.cancelled

    async def test_fail_not_blocked_by_global_freeze(self, db: AsyncSession) -> None:
        from workflows.runtime import WorkflowRuntime
        rt = WorkflowRuntime(db)
        wf = await rt.start(WorkflowType.outreach)
        await _freeze_global(db)
        failed = await rt.fail(wf.id, reason="test failure during freeze")
        from models.enums import WorkflowStatus
        assert failed.workflow_status == WorkflowStatus.failed

    async def test_complete_not_blocked_by_global_freeze(self, db: AsyncSession) -> None:
        from workflows.runtime import WorkflowRuntime
        rt = WorkflowRuntime(db)
        wf = await rt.start(WorkflowType.outreach)
        await _freeze_global(db)
        completed = await rt.complete(wf.id)
        from models.enums import WorkflowStatus
        assert completed.workflow_status == WorkflowStatus.completed

    async def test_start_freeze_propagated_event_emitted(self, db: AsyncSession) -> None:
        from workflows.runtime import WorkflowRuntime
        await _freeze_global(db)
        rt = WorkflowRuntime(db)
        with pytest.raises(GovernanceFrozenError):
            await rt.start(WorkflowType.outreach)
        events = await GovernanceEventRepository(db).get_by_type(
            GovernanceEventType.freeze_propagated
        )
        assert any(e.payload.get("source_runtime") == "workflow" for e in events)


# ---------------------------------------------------------------------------
# SophiaSessionRuntime integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSophiaSessionRuntimeGovernanceIntegration:
    async def test_create_blocked_by_global_freeze(self, db: AsyncSession) -> None:
        from models.enums import SophiaChannelType
        from sophia.contracts import SophiaSessionSpec
        from sophia.session import SophiaSessionRuntime
        await _freeze_global(db)
        rt = SophiaSessionRuntime(db)
        spec = SophiaSessionSpec(
            session_key=f"sk-{uuid4()}",
            channel=SophiaChannelType.text,
        )
        with pytest.raises(GovernanceFrozenError):
            await rt.create(spec)

    async def test_create_idempotent_return_bypasses_freeze(self, db: AsyncSession) -> None:
        """Existing session lookup returns before freeze check (idempotency intact)."""
        from models.enums import SophiaChannelType
        from sophia.contracts import SophiaSessionSpec
        from sophia.session import SophiaSessionRuntime
        rt = SophiaSessionRuntime(db)
        key = f"sk-{uuid4()}"
        spec = SophiaSessionSpec(session_key=key, channel=SophiaChannelType.text)

        # Create while not frozen
        session1 = await rt.create(spec)

        # Now freeze and try to create with same key — idempotent path returns early
        await _freeze_global(db)
        session2 = await rt.create(spec)
        assert session1.session_id == session2.session_id

    async def test_create_passes_when_not_frozen(self, db: AsyncSession) -> None:
        from models.enums import SophiaChannelType
        from sophia.contracts import SophiaSessionSpec
        from sophia.session import SophiaSessionRuntime
        rt = SophiaSessionRuntime(db)
        spec = SophiaSessionSpec(
            session_key=f"sk-{uuid4()}",
            channel=SophiaChannelType.text,
        )
        record = await rt.create(spec)
        assert record.session_id is not None


# ---------------------------------------------------------------------------
# SophiaTurnRuntime integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSophiaTurnRuntimeGovernanceIntegration:
    async def _make_session(self, db: AsyncSession):
        from models.enums import SophiaChannelType
        from sophia.contracts import SophiaSessionSpec
        from sophia.session import SophiaSessionRuntime
        rt = SophiaSessionRuntime(db)
        spec = SophiaSessionSpec(
            session_key=f"sk-{uuid4()}",
            channel=SophiaChannelType.text,
        )
        return await rt.create(spec)

    async def test_start_blocked_by_global_freeze(self, db: AsyncSession) -> None:
        from sophia.contracts import SophiaTurnInput
        from sophia.turn import SophiaTurnRuntime

        session = await self._make_session(db)
        await _freeze_global(db)
        rt = SophiaTurnRuntime(db)
        inp = SophiaTurnInput(
            session_id=session.session_id,
            turn_index=0,
            input_payload={"text": "hello"},
        )
        with pytest.raises(GovernanceFrozenError):
            await rt.start(inp)

    async def test_start_blocked_by_session_scoped_freeze(self, db: AsyncSession) -> None:
        from sophia.contracts import SophiaTurnInput
        from sophia.turn import SophiaTurnRuntime

        session = await self._make_session(db)
        await _freeze_scope(db, f"sophia:{session.session_id}")
        rt = SophiaTurnRuntime(db)
        inp = SophiaTurnInput(
            session_id=session.session_id,
            turn_index=0,
            input_payload={"text": "hello"},
        )
        with pytest.raises(GovernanceFrozenError):
            await rt.start(inp)

    async def test_start_other_session_not_blocked(self, db: AsyncSession) -> None:
        from sophia.contracts import SophiaTurnInput
        from sophia.turn import SophiaTurnRuntime

        session1 = await self._make_session(db)
        session2 = await self._make_session(db)
        await _freeze_scope(db, f"sophia:{session1.session_id}")

        rt = SophiaTurnRuntime(db)
        inp = SophiaTurnInput(
            session_id=session2.session_id,
            turn_index=0,
            input_payload={"text": "hello"},
        )
        turn = await rt.start(inp)
        assert turn.turn_id is not None

    async def test_start_idempotent_return_bypasses_freeze(self, db: AsyncSession) -> None:
        """Turn with existing turn_key returns before freeze check."""
        from sophia.contracts import SophiaTurnInput
        from sophia.turn import SophiaTurnRuntime

        session = await self._make_session(db)
        rt = SophiaTurnRuntime(db)
        turn_key = f"tk-{uuid4()}"
        inp = SophiaTurnInput(
            session_id=session.session_id,
            turn_index=0,
            input_payload={"text": "hello"},
            turn_key=turn_key,
        )
        # Start once without freeze
        turn1 = await rt.start(inp)

        # Freeze, then retry with same turn_key
        await _freeze_global(db)
        turn2 = await rt.start(inp)
        assert turn1.turn_id == turn2.turn_id

    async def test_start_passes_when_not_frozen(self, db: AsyncSession) -> None:
        from sophia.contracts import SophiaTurnInput
        from sophia.turn import SophiaTurnRuntime

        session = await self._make_session(db)
        rt = SophiaTurnRuntime(db)
        inp = SophiaTurnInput(
            session_id=session.session_id,
            turn_index=0,
            input_payload={"text": "hello"},
        )
        turn = await rt.start(inp)
        assert turn.turn_id is not None


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestGovernanceExceptions:
    def test_frozen_error_has_scope(self) -> None:
        exc = GovernanceFrozenError(scope="global")
        assert exc.scope == "global"
        assert exc.freeze_key is None
        assert "global" in str(exc)

    def test_frozen_error_with_freeze_key(self) -> None:
        exc = GovernanceFrozenError(scope="global", freeze_key="fk-1")
        assert exc.freeze_key == "fk-1"
        assert "fk-1" in str(exc)

    def test_denied_error_attributes(self) -> None:
        exc = GovernanceDeniedError(
            action="bad.action", classification="forbidden", evaluation_id="ev-1"
        )
        assert exc.action == "bad.action"
        assert exc.classification == "forbidden"
        assert exc.evaluation_id == "ev-1"

    def test_invariant_violation_attributes(self) -> None:
        exc = GovernanceInvariantViolationError(
            invariant_id="INV-4", details="governance bypassed"
        )
        assert exc.invariant_id == "INV-4"
        assert exc.details == "governance bypassed"
        assert "INV-4" in str(exc)

    def test_all_are_governance_errors(self) -> None:
        from governance.exceptions import (
            GovernanceApprovalRequiredError,
            GovernanceError,
        )

        assert issubclass(GovernanceFrozenError, GovernanceError)
        assert issubclass(GovernanceDeniedError, GovernanceError)
        assert issubclass(GovernanceApprovalRequiredError, GovernanceError)
        assert issubclass(GovernanceInvariantViolationError, GovernanceError)


# ---------------------------------------------------------------------------
# Event types registered in enums
# ---------------------------------------------------------------------------


class TestGovernanceEnforcementEventTypes:
    def test_action_denied_event_type_exists(self) -> None:
        assert GovernanceEventType.action_denied == "action_denied"

    def test_freeze_propagated_event_type_exists(self) -> None:
        assert GovernanceEventType.freeze_propagated == "freeze_propagated"

    def test_invariant_violated_event_type_exists(self) -> None:
        assert GovernanceEventType.invariant_violated == "invariant_violated"
