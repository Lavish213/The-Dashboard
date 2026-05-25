"""
GovernanceRuntime — Phase 14 session-scoped coordinator.

Single import point for callers that need the full governance surface.
Instantiates all Phase 11 primitives + Phase 14 engine on one AsyncSession.

Usage:
    gov = GovernanceRuntime(session)
    await gov.enforce("workflow.start", RiskTier.elevated)
    await gov.check_freeze("global")
    await gov.freeze.activate("fk-x", "global", "emergency halt")

Properties expose Phase 11 primitives without re-instantiation overhead:
  engine, freeze, policy, router, escalation, override, audit,
  delegation, metrics, snapshot, reconstruction

Convenience delegates (thin forwarding to engine):
  enforce(action, risk_tier, scope, actor_id, context, source_runtime)
  check_freeze(scope, actor_id, source_runtime)
  evaluate(action, risk_tier, actor_id, workflow_id, context)

Architecture:
  - All properties are lazily initialized (created on first access).
  - Shares the same AsyncSession across all primitives — single transaction.
  - Does NOT duplicate Phase 11 logic.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from governance.audit import GovernanceAuditRuntime
from governance.contracts import PolicyEvaluationResult
from governance.delegation import DelegationRuntime
from governance.engine import GovernanceEngine
from governance.escalation import EscalationChainRuntime
from governance.freeze import FreezeRuntime
from governance.metrics import GovernanceMetricsRuntime
from governance.override import EmergencyOverrideRuntime
from governance.policy import GovernancePolicyRuntime
from governance.reconstruction import ApprovalHistoryReconstructor
from governance.router import ApprovalRouter
from governance.snapshot import GovernancePolicySnapshotRuntime
from models.enums import RiskTier


class GovernanceRuntime:
    """
    Session-scoped governance coordinator.

    Holds all governance primitive instances sharing one AsyncSession.
    Provides convenience delegates to GovernanceEngine for common
    enforcement patterns.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        # Lazy-initialized primitives — created on first property access
        self._engine: GovernanceEngine | None = None
        self._freeze: FreezeRuntime | None = None
        self._policy: GovernancePolicyRuntime | None = None
        self._router: ApprovalRouter | None = None
        self._escalation: EscalationChainRuntime | None = None
        self._override: EmergencyOverrideRuntime | None = None
        self._audit: GovernanceAuditRuntime | None = None
        self._delegation: DelegationRuntime | None = None
        self._metrics: GovernanceMetricsRuntime | None = None
        self._snapshot: GovernancePolicySnapshotRuntime | None = None
        self._reconstruction: ApprovalHistoryReconstructor | None = None

    # ------------------------------------------------------------------
    # Primitive accessors
    # ------------------------------------------------------------------

    @property
    def engine(self) -> GovernanceEngine:
        if self._engine is None:
            self._engine = GovernanceEngine(self._session)
        return self._engine

    @property
    def freeze(self) -> FreezeRuntime:
        if self._freeze is None:
            self._freeze = FreezeRuntime(self._session)
        return self._freeze

    @property
    def policy(self) -> GovernancePolicyRuntime:
        if self._policy is None:
            self._policy = GovernancePolicyRuntime(self._session)
        return self._policy

    @property
    def router(self) -> ApprovalRouter:
        if self._router is None:
            self._router = ApprovalRouter(self._session)
        return self._router

    @property
    def escalation(self) -> EscalationChainRuntime:
        if self._escalation is None:
            self._escalation = EscalationChainRuntime(self._session)
        return self._escalation

    @property
    def override(self) -> EmergencyOverrideRuntime:
        if self._override is None:
            self._override = EmergencyOverrideRuntime(self._session)
        return self._override

    @property
    def audit(self) -> GovernanceAuditRuntime:
        if self._audit is None:
            self._audit = GovernanceAuditRuntime(self._session)
        return self._audit

    @property
    def delegation(self) -> DelegationRuntime:
        if self._delegation is None:
            self._delegation = DelegationRuntime(self._session)
        return self._delegation

    @property
    def metrics(self) -> GovernanceMetricsRuntime:
        if self._metrics is None:
            self._metrics = GovernanceMetricsRuntime(self._session)
        return self._metrics

    @property
    def snapshot(self) -> GovernancePolicySnapshotRuntime:
        if self._snapshot is None:
            self._snapshot = GovernancePolicySnapshotRuntime(self._session)
        return self._snapshot

    @property
    def reconstruction(self) -> ApprovalHistoryReconstructor:
        if self._reconstruction is None:
            self._reconstruction = ApprovalHistoryReconstructor(self._session)
        return self._reconstruction

    # ------------------------------------------------------------------
    # Convenience delegates → GovernanceEngine
    # ------------------------------------------------------------------

    async def enforce(
        self,
        action: str,
        risk_tier: RiskTier,
        scope: str | None = None,
        actor_id: UUID | None = None,
        workflow_id: UUID | None = None,
        context: dict | None = None,
        source_runtime: str = "unknown",
    ) -> PolicyEvaluationResult:
        """
        Full enforcement — freeze + policy evaluation + audit + deny gate.
        Raises GovernanceFrozenError or GovernanceDeniedError on block.
        """
        return await self.engine.enforce_action(
            action=action,
            risk_tier=risk_tier,
            scope=scope,
            actor_id=actor_id,
            workflow_id=workflow_id,
            context=context,
            source_runtime=source_runtime,
        )

    async def check_freeze(
        self,
        scope: str,
        actor_id: UUID | None = None,
        source_runtime: str = "unknown",
    ) -> None:
        """
        Freeze-only check. Raises GovernanceFrozenError if frozen.
        Does not evaluate policy. Use for operations that don't have an
        action string but must still respect freeze state.
        """
        await self.engine.check_freeze(
            scope=scope,
            actor_id=actor_id,
            source_runtime=source_runtime,
        )

    async def evaluate(
        self,
        action: str,
        risk_tier: RiskTier,
        actor_id: UUID | None = None,
        workflow_id: UUID | None = None,
        context: dict | None = None,
    ) -> PolicyEvaluationResult:
        """
        Pure evaluation — no enforcement, no events, no freeze check.
        Safe to call during replay.
        """
        return await self.engine.evaluate_action(
            action=action,
            risk_tier=risk_tier,
            actor_id=actor_id,
            workflow_id=workflow_id,
            context=context,
        )
