"""
ApprovalPolicyRuntime: deterministic policy evaluation for approval requirements.

Pure rule evaluation. Stateless. No DB. No side effects.
Replay-safe: same inputs always produce same output.
NO AI. NO learning systems.
"""

from dataclasses import dataclass

from models.enums import ApprovalType, RiskLevel, WorkflowType


@dataclass(frozen=True)
class PolicyDecision:
    requires_approval: bool
    approval_type: ApprovalType | None
    risk_level: RiskLevel
    reason: str


# Risk level -> requires approval (deterministic threshold rules)
RISK_APPROVAL_THRESHOLD: dict[RiskLevel, bool] = {
    RiskLevel.low: False,
    RiskLevel.medium: True,
    RiskLevel.high: True,
    RiskLevel.critical: True,
}

# Workflow type -> required approval types (operator-controlled, statically defined)
WORKFLOW_APPROVAL_MAP: dict[WorkflowType, list[ApprovalType]] = {
    WorkflowType.outreach: [ApprovalType.outreach],
    WorkflowType.closing: [ApprovalType.offer],
    WorkflowType.qualification: [ApprovalType.skip_trace],
    WorkflowType.follow_up: [],
}


class ApprovalPolicyRuntime:
    """
    Stateless deterministic policy evaluator.
    No DB. No side effects. Pure input -> PolicyDecision.
    """

    def evaluate_risk(self, risk_level: RiskLevel) -> PolicyDecision:
        """Return whether this risk level mandates approval."""
        requires = RISK_APPROVAL_THRESHOLD.get(risk_level, True)
        return PolicyDecision(
            requires_approval=requires,
            approval_type=None,
            risk_level=risk_level,
            reason=f"risk_level={risk_level} threshold={'exceeded' if requires else 'not_exceeded'}",
        )

    def evaluate_workflow_type(
        self,
        workflow_type: WorkflowType,
        risk_level: RiskLevel = RiskLevel.low,
    ) -> PolicyDecision:
        """Return required approval type for a workflow type + risk level combination."""
        required_types = WORKFLOW_APPROVAL_MAP.get(workflow_type, [])
        risk_requires = RISK_APPROVAL_THRESHOLD.get(risk_level, False)
        requires = bool(required_types) or risk_requires

        return PolicyDecision(
            requires_approval=requires,
            approval_type=required_types[0] if required_types else None,
            risk_level=risk_level,
            reason=(
                f"workflow_type={workflow_type} "
                f"required_types={[t for t in required_types]} "
                f"risk={risk_level}"
            ),
        )

    def evaluate_action(
        self,
        action: str,
        risk_level: RiskLevel,
        workflow_type: WorkflowType | None = None,
    ) -> PolicyDecision:
        """
        General action policy evaluation.
        Combines risk threshold and workflow type rules.
        Risk threshold takes precedence if it mandates approval.
        """
        risk_decision = self.evaluate_risk(risk_level)
        if risk_decision.requires_approval:
            return risk_decision

        if workflow_type is not None:
            return self.evaluate_workflow_type(workflow_type, risk_level)

        return PolicyDecision(
            requires_approval=False,
            approval_type=None,
            risk_level=risk_level,
            reason=f"action={action} risk={risk_level} no_policy_match",
        )
