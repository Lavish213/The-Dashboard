"""
Workflow state machine definition.

States, terminal states, and valid transitions are the single source of truth.
No logic here — pure data.
"""

from models.enums import WorkflowStatus

# States from which no transition is possible
TERMINAL_STATES: frozenset[WorkflowStatus] = frozenset({
    WorkflowStatus.completed,
    WorkflowStatus.failed,
    WorkflowStatus.cancelled,
})

# Valid transitions: from_state -> set of allowed to_states
VALID_TRANSITIONS: dict[WorkflowStatus, frozenset[WorkflowStatus]] = {
    WorkflowStatus.pending: frozenset({
        WorkflowStatus.active,
        WorkflowStatus.cancelled,
    }),
    WorkflowStatus.active: frozenset({
        WorkflowStatus.paused,
        WorkflowStatus.completed,
        WorkflowStatus.failed,
        WorkflowStatus.cancelled,
    }),
    WorkflowStatus.paused: frozenset({
        WorkflowStatus.active,
        WorkflowStatus.cancelled,
    }),
    WorkflowStatus.completed: frozenset(),
    WorkflowStatus.failed: frozenset(),
    WorkflowStatus.cancelled: frozenset(),
}


def is_terminal(status: WorkflowStatus) -> bool:
    return status in TERMINAL_STATES


def is_valid_transition(from_status: WorkflowStatus, to_status: WorkflowStatus) -> bool:
    return to_status in VALID_TRANSITIONS.get(from_status, frozenset())
