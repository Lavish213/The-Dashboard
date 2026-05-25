"""
PolicyEvaluator — deterministic, pure policy evaluation.

Takes a list of GovernancePolicySnapshot objects and an action string.
Returns a PolicyEvaluationResult without any DB writes.

Pattern matching uses fnmatch:
  "workflow.*"         — matches any workflow action
  "ai.tool.*"         — matches any AI tool action
  "*"                 — matches everything
  "workflow.offer.create" — exact match

Most-restrictive wins when multiple policies match:
  forbidden > privileged > restricted > safe

Policy inheritance: inherited_from → merge parent rules before child override.
"""
from __future__ import annotations

import fnmatch
from uuid import UUID, uuid4

from governance.contracts import (
    EscalationStep,
    GovernancePolicySnapshot,
    PolicyEvaluationInput,
    PolicyEvaluationResult,
)
from models.enums import (
    ActionClassification,
    ApprovalRoutingStrategy,
    ApprovalType,
)

_CLASSIFICATION_RANK: dict[ActionClassification, int] = {
    ActionClassification.safe: 0,
    ActionClassification.restricted: 1,
    ActionClassification.privileged: 2,
    ActionClassification.forbidden: 3,
}

# Default policy when no match found — safe, no approval
_DEFAULT_RESULT_TEMPLATE = dict(
    classification=ActionClassification.safe,
    requires_approval=False,
    approval_type=None,
    routing_strategy=ApprovalRoutingStrategy.direct,
    approver_ids=(),
    escalation_chain=(),
    quorum_required=0,
    timeout_seconds=86400,
    matched_policy_key=None,
    matched_policy_version=0,
)


def _matches(action: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(action, p) for p in patterns)


def _requires_approval(classification: ActionClassification) -> bool:
    return classification in (
        ActionClassification.restricted,
        ActionClassification.privileged,
    )


def _infer_approval_type(action: str, rules: dict) -> ApprovalType | None:
    """Extract approval_type from policy rules, or infer from action prefix."""
    if "approval_type" in rules:
        try:
            return ApprovalType(rules["approval_type"])
        except ValueError:
            pass
    # Infer from action
    if action.startswith("workflow.offer"):
        return ApprovalType.offer
    if action.startswith("workflow.price"):
        return ApprovalType.price_reduction
    if action.startswith("workflow.skip_trace") or "skip_trace" in action:
        return ApprovalType.skip_trace
    return ApprovalType.outreach


class PolicyEvaluator:
    """
    Pure, stateless policy evaluator.

    evaluate(inp, policies) → PolicyEvaluationResult

    policies: active snapshots, ordered by policy_key (caller fetches from DB).
    Inheritance: if a policy has inherited_from, caller must include parent.
    """

    def evaluate(
        self,
        inp: PolicyEvaluationInput,
        policies: list[GovernancePolicySnapshot],
    ) -> PolicyEvaluationResult:
        """
        Evaluate action against all policies. Most-restrictive wins.

        1. Filter only active policies.
        2. Resolve inheritance (parent merged first, child overrides).
        3. Find all matching policies by action_patterns.
        4. Pick highest classification rank.
        5. Build result from winning policy.
        """
        active = [p for p in policies if p.status == p.status.active]
        resolved = self._resolve_inheritance(active)
        matching = [p for p in resolved if _matches(inp.action, p.action_patterns)]

        if not matching:
            return PolicyEvaluationResult(
                action=inp.action,
                risk_tier=inp.risk_tier,
                evaluation_id=str(uuid4()),
                **_DEFAULT_RESULT_TEMPLATE,  # type: ignore[arg-type]
            )

        # Pick most restrictive
        winner = max(matching, key=lambda p: _CLASSIFICATION_RANK[p.classification])

        requires_appr = _requires_approval(winner.classification)
        approval_type = _infer_approval_type(inp.action, winner.rules) if requires_appr else None

        chain = tuple(
            EscalationStep(
                escalate_to=UUID(step["escalate_to"]),
                after_seconds=step["after_seconds"],
                reason=step.get("reason"),
            )
            for step in winner.escalation_chain
        )

        return PolicyEvaluationResult(
            action=inp.action,
            classification=winner.classification,
            risk_tier=winner.risk_tier,
            requires_approval=requires_appr,
            approval_type=approval_type,
            routing_strategy=winner.routing_strategy,
            approver_ids=winner.approver_ids,
            escalation_chain=chain,
            quorum_required=winner.quorum_required,
            timeout_seconds=winner.timeout_seconds,
            matched_policy_key=winner.policy_key,
            matched_policy_version=winner.version,
            evaluation_id=str(uuid4()),
        )

    def _resolve_inheritance(
        self,
        policies: list[GovernancePolicySnapshot],
    ) -> list[GovernancePolicySnapshot]:
        """
        Resolve inherited_from chains.

        Child policies inherit parent action_patterns unless they define their own.
        Rules are shallow-merged (child keys override parent).
        Returns a new list where each policy has fully-resolved patterns + rules.
        """
        by_key: dict[str, GovernancePolicySnapshot] = {}
        for p in policies:
            existing = by_key.get(p.policy_key)
            if existing is None or p.version > existing.version:
                by_key[p.policy_key] = p

        resolved = []
        for pol in by_key.values():
            if pol.inherited_from and pol.inherited_from in by_key:
                parent = by_key[pol.inherited_from]
                merged_rules = {**parent.rules, **pol.rules}
                merged_patterns = (
                    pol.action_patterns if pol.action_patterns else parent.action_patterns
                )
                from dataclasses import replace
                pol = replace(pol, rules=merged_rules, action_patterns=merged_patterns)
            resolved.append(pol)
        return resolved

    def classify_action(self, action: str, policies: list[GovernancePolicySnapshot]) -> ActionClassification:
        """Quick classification without full evaluation context."""
        active = [p for p in policies if p.status == p.status.active]
        resolved = self._resolve_inheritance(active)
        matching = [p for p in resolved if _matches(action, p.action_patterns)]
        if not matching:
            return ActionClassification.safe
        return max(
            (p.classification for p in matching),
            key=lambda c: _CLASSIFICATION_RANK[c],
        )
