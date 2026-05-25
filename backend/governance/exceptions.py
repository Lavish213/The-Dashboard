"""
Governance exception hierarchy — Phase 14.

GovernanceError            — base for all governance failures.
GovernanceFrozenError      — scope frozen or kill switch active. Hard block.
GovernanceDeniedError      — action forbidden by policy. Hard block.
GovernanceApprovalRequiredError — action requires approval before proceeding.
                              Not a terminal failure — caller gates on approval.
GovernanceInvariantViolationError — runtime invariant violated. Hard block.

These exceptions are raised by GovernanceEngine. Callers must handle them
explicitly. No silent continuation is permitted on frozen/denied/violated state.
"""
from __future__ import annotations


class GovernanceError(Exception):
    """Base exception for all governance runtime failures."""


class GovernanceFrozenError(GovernanceError):
    """
    Raised when the target scope is frozen or a kill switch is active.

    scope      — the frozen scope string (e.g. "global", "workflow:{uuid}")
    freeze_key — the freeze key that is active, if known
    """

    def __init__(self, scope: str, freeze_key: str | None = None) -> None:
        self.scope = scope
        self.freeze_key = freeze_key
        msg = f"Execution frozen: scope={scope!r}"
        if freeze_key:
            msg += f" freeze_key={freeze_key!r}"
        super().__init__(msg)


class GovernanceDeniedError(GovernanceError):
    """
    Raised when an action is classified as forbidden by active policy.

    action         — the action string that was denied
    classification — the ActionClassification value (always "forbidden")
    evaluation_id  — unique ID of the policy evaluation that denied this action
    """

    def __init__(self, action: str, classification: str, evaluation_id: str) -> None:
        self.action = action
        self.classification = classification
        self.evaluation_id = evaluation_id
        super().__init__(
            f"Action denied: {action!r} classification={classification!r} "
            f"evaluation_id={evaluation_id}"
        )


class GovernanceApprovalRequiredError(GovernanceError):
    """
    Raised when an action requires approval before execution may proceed.

    Not a terminal failure — callers should:
      1. Create an approval request via ApprovalRouter
      2. Gate execution until approval is resolved
      3. Resume execution on approval grant

    action        — the action string requiring approval
    evaluation_id — unique ID of the policy evaluation that flagged this action
    """

    def __init__(self, action: str, evaluation_id: str) -> None:
        self.action = action
        self.evaluation_id = evaluation_id
        super().__init__(
            f"Approval required: {action!r} evaluation_id={evaluation_id}"
        )


class GovernanceInvariantViolationError(GovernanceError):
    """
    Raised when a runtime invariant is violated.

    invariant_id — identifier matching RUNTIME_INVARIANTS.md (e.g. "INV-4")
    details      — human-readable description of the violation
    """

    def __init__(self, invariant_id: str, details: str) -> None:
        self.invariant_id = invariant_id
        self.details = details
        super().__init__(f"Invariant violated: {invariant_id} — {details}")
