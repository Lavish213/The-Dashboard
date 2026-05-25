"""
GovernanceEngine — Phase 14 enforcement entry point.

Composes existing Phase 11 primitives (PolicyEvaluator, FreezeRuntime,
GovernanceAuditRuntime) into a deterministic enforcement surface.

Public interface:

  check_freeze(scope, actor_id, source_runtime)
    → None on pass.
    → Raises GovernanceFrozenError if global or scope is frozen.
    → Emits freeze_propagated event on block.

  evaluate_action(action, risk_tier, actor_id, workflow_id, context)
    → PolicyEvaluationResult (pure evaluation; no exceptions; no events).
    → Used for inspection and replay-safe queries.

  enforce_action(action, risk_tier, scope, actor_id, workflow_id, context, source_runtime)
    → PolicyEvaluationResult on pass.
    → Raises GovernanceFrozenError if frozen.
    → Raises GovernanceDeniedError if classification == forbidden.
    → Emits audit record and action_denied event on deny.
    → Does NOT raise for requires_approval — caller checks result.requires_approval.

Architecture:
  - Does NOT duplicate Phase 11 primitives.
  - Does NOT own policy CRUD, approval routing, escalation, quorum, delegation.
  - Callers needing those use GovernanceRuntime (governance/runtime.py).
  - Replay callers should use evaluate_action() — no enforcement, no events.

Invariants enforced:
  INV-4  — Governance cannot be bypassed.
  INV-7  — Tools are deny-by-default (forbidden = blocked, no exceptions).
  INV-18 — Cancellation must propagate (terminal states not blocked by engine).
  INV-24 — Production runtime must fail closed (frozen/forbidden → raise).
"""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from governance.audit import ACTION_POLICY_EVALUATED, GovernanceAuditRuntime
from governance.contracts import PolicyEvaluationInput, PolicyEvaluationResult
from governance.evaluator import PolicyEvaluator
from governance.events import emit_action_denied, emit_freeze_propagated
from governance.exceptions import GovernanceDeniedError, GovernanceFrozenError
from governance.freeze import FreezeRuntime
from models.enums import ActionClassification, RiskTier
from repositories.governance_policy import GovernancePolicyRepository

logger = structlog.get_logger(__name__)

_GLOBAL_SCOPE = "global"


class GovernanceEngine:
    """
    Session-scoped governance enforcement entry point.

    Instantiate once per request/session. Shares the same AsyncSession
    as the calling runtime to participate in the same transaction.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._freeze = FreezeRuntime(session)
        self._evaluator = PolicyEvaluator()
        self._policies = GovernancePolicyRepository(session)
        self._audit = GovernanceAuditRuntime(session)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def check_freeze(
        self,
        scope: str,
        actor_id: UUID | None = None,
        source_runtime: str = "unknown",
    ) -> None:
        """
        Raise GovernanceFrozenError if scope or global scope is frozen.

        Order:
          1. Check "global" scope (unless scope IS "global").
          2. Check provided scope.

        Emits freeze_propagated on every block (INV-4, INV-24).
        Returns None if neither scope is frozen.
        """
        if scope != _GLOBAL_SCOPE:
            if await self._freeze.is_frozen(_GLOBAL_SCOPE):
                await emit_freeze_propagated(
                    self._session,
                    scope=_GLOBAL_SCOPE,
                    source_runtime=source_runtime,
                    actor_id=actor_id,
                )
                logger.warning(
                    "governance.freeze.propagated",
                    scope=_GLOBAL_SCOPE,
                    source_runtime=source_runtime,
                )
                raise GovernanceFrozenError(scope=_GLOBAL_SCOPE)

        if await self._freeze.is_frozen(scope):
            await emit_freeze_propagated(
                self._session,
                scope=scope,
                source_runtime=source_runtime,
                actor_id=actor_id,
            )
            logger.warning(
                "governance.freeze.propagated",
                scope=scope,
                source_runtime=source_runtime,
            )
            raise GovernanceFrozenError(scope=scope)

    async def evaluate_action(
        self,
        action: str,
        risk_tier: RiskTier,
        actor_id: UUID | None = None,
        workflow_id: UUID | None = None,
        context: dict | None = None,
    ) -> PolicyEvaluationResult:
        """
        Pure policy evaluation — no exceptions, no events, no freeze check.

        Returns PolicyEvaluationResult for caller inspection.
        Safe to call during replay — does not alter runtime state.
        """
        policies = await self._policies.get_active()
        inp = PolicyEvaluationInput(
            action=action,
            risk_tier=risk_tier,
            actor_id=actor_id,
            workflow_id=workflow_id,
            context=context or {},
        )
        return self._evaluator.evaluate(inp, policies)

    async def enforce_action(
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
        Full governance enforcement for an action.

        Enforcement order:
          1. Freeze gate — GovernanceFrozenError if global/scope frozen.
          2. Policy evaluation.
          3. Audit record emitted.
          4. Deny gate — GovernanceDeniedError if classification == forbidden.
          5. Return result (caller checks result.requires_approval for gate).

        Raises:
          GovernanceFrozenError      — scope or global scope is frozen.
          GovernanceDeniedError      — action is classified forbidden.

        Does NOT raise GovernanceApprovalRequiredError.
        Caller checks result.requires_approval and routes approval if needed.

        Replay callers must use evaluate_action() — enforce_action() is not
        replay-safe (it raises on governance state that already resolved).
        """
        enforce_scope = scope or _GLOBAL_SCOPE

        # Step 1 — freeze gate
        await self.check_freeze(
            scope=enforce_scope,
            actor_id=actor_id,
            source_runtime=source_runtime,
        )

        # Step 2 — policy evaluation
        result = await self.evaluate_action(
            action=action,
            risk_tier=risk_tier,
            actor_id=actor_id,
            workflow_id=workflow_id,
            context=context,
        )

        # Step 3 — audit trail (always written for enforce calls, INV-3)
        await self._audit.record(
            action=ACTION_POLICY_EVALUATED,
            payload={
                "action": action,
                "classification": result.classification.value,
                "risk_tier": risk_tier.value,
                "requires_approval": result.requires_approval,
                "evaluation_id": result.evaluation_id,
                "matched_policy_key": result.matched_policy_key,
                "scope": enforce_scope,
                "source_runtime": source_runtime,
            },
            actor_id=actor_id,
        )

        # Step 4 — deny gate (INV-4, INV-7, INV-24)
        if result.classification == ActionClassification.forbidden:
            await emit_action_denied(
                self._session,
                action=action,
                classification=result.classification.value,
                evaluation_id=result.evaluation_id,
                scope=enforce_scope,
                actor_id=actor_id,
            )
            logger.warning(
                "governance.action.denied",
                action=action,
                classification=result.classification.value,
                scope=enforce_scope,
                source_runtime=source_runtime,
            )
            raise GovernanceDeniedError(
                action=action,
                classification=result.classification.value,
                evaluation_id=result.evaluation_id,
            )

        return result
