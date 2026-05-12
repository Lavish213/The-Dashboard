"""
Workflow transition guards.

Single responsibility: validate whether a transition is allowed.
Raises on invalid. Returns target status on valid.
"""

from dataclasses import dataclass
from uuid import UUID

from models.enums import WorkflowStatus
from workflows.states import is_terminal, is_valid_transition


class TransitionError(Exception):
    """Raised when a workflow transition is not allowed."""

    def __init__(self, workflow_id: UUID, from_status: WorkflowStatus, to_status: WorkflowStatus, reason: str = ""):
        self.workflow_id = workflow_id
        self.from_status = from_status
        self.to_status = to_status
        msg = f"Workflow {workflow_id}: cannot transition {from_status} -> {to_status}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


@dataclass(frozen=True)
class TransitionResult:
    workflow_id: UUID
    from_status: WorkflowStatus
    to_status: WorkflowStatus


def validate_transition(
    workflow_id: UUID,
    current_status: WorkflowStatus,
    target_status: WorkflowStatus,
) -> TransitionResult:
    """
    Validate and return a transition result.
    Raises TransitionError if not allowed.
    """
    if is_terminal(current_status):
        raise TransitionError(
            workflow_id, current_status, target_status,
            reason=f"{current_status} is terminal",
        )

    if not is_valid_transition(current_status, target_status):
        raise TransitionError(
            workflow_id, current_status, target_status,
        )

    return TransitionResult(
        workflow_id=workflow_id,
        from_status=current_status,
        to_status=target_status,
    )
