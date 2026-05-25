"""
Workflow step graph — canonical step sequences and transition validation.

Advisory validator: prevents backward step transitions for known steps.
Unknown steps (custom/ad-hoc) pass without restriction.
Complements the status-level transition guard in transitions.py.
"""
from __future__ import annotations

from models.enums import WorkflowType

# Canonical ordered step sequences per workflow type.
# Steps are forward-only: index(next) > index(current).
STEP_GRAPH: dict[WorkflowType, list[str]] = {
    WorkflowType.outreach: ["contacted", "qualified", "offered", "closed"],
    WorkflowType.qualification: ["initial_review", "scored", "qualified", "rejected"],
    WorkflowType.follow_up: ["scheduled", "contacted", "resolved"],
    WorkflowType.closing: ["negotiating", "under_contract", "closed"],
}


class StepTransitionError(Exception):
    def __init__(
        self,
        workflow_type: WorkflowType,
        from_step: str | None,
        to_step: str,
        reason: str = "",
    ) -> None:
        msg = f"{workflow_type}: {from_step!r} → {to_step!r} not allowed"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)
        self.workflow_type = workflow_type
        self.from_step = from_step
        self.to_step = to_step


def validate_step_advance(
    workflow_type: WorkflowType,
    current_step: str | None,
    next_step: str,
) -> None:
    """
    Validate next_step is a forward move for known steps.
    Raises StepTransitionError on backward transition of known steps.
    Unknown steps (not in STEP_GRAPH) are always allowed.
    """
    steps = STEP_GRAPH.get(workflow_type)
    if steps is None or current_step is None:
        return  # no graph or first step — unrestricted

    if current_step not in steps or next_step not in steps:
        return  # unknown step — no restriction

    if steps.index(next_step) <= steps.index(current_step):
        raise StepTransitionError(
            workflow_type, current_step, next_step, "backward transition not allowed"
        )


def get_valid_next_steps(
    workflow_type: WorkflowType,
    current_step: str | None,
) -> list[str]:
    """
    Return valid forward steps from current_step.
    Returns all steps if current_step is None (first advance).
    Returns [] if current_step is the terminal step or unknown.
    """
    steps = STEP_GRAPH.get(workflow_type, [])
    if current_step is None:
        return list(steps)
    if current_step not in steps:
        return []
    idx = steps.index(current_step)
    return steps[idx + 1 :]


def is_valid_step(workflow_type: WorkflowType, step: str) -> bool:
    """Return True if step is a canonical step for this workflow type."""
    return step in STEP_GRAPH.get(workflow_type, [])
