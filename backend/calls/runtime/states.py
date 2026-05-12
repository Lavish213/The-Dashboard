"""Call session state machine — deterministic transitions only."""
from models.enums import CallSessionStatus

TERMINAL_STATES: frozenset[CallSessionStatus] = frozenset({
    CallSessionStatus.completed,
    CallSessionStatus.failed,
})

VALID_TRANSITIONS: dict[CallSessionStatus, frozenset[CallSessionStatus]] = {
    CallSessionStatus.waiting: frozenset({
        CallSessionStatus.active,
        CallSessionStatus.failed,
    }),
    CallSessionStatus.active: frozenset({
        CallSessionStatus.completed,
        CallSessionStatus.failed,
    }),
    CallSessionStatus.completed: frozenset(),
    CallSessionStatus.failed: frozenset(),
}


class CallSessionTransitionError(Exception):
    def __init__(
        self,
        session_id,
        from_status: CallSessionStatus,
        to_status: CallSessionStatus,
        reason: str = "",
    ) -> None:
        self.session_id = session_id
        self.from_status = from_status
        self.to_status = to_status
        msg = f"CallSession {session_id}: cannot transition {from_status} -> {to_status}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


def is_terminal(status: CallSessionStatus) -> bool:
    return status in TERMINAL_STATES


def validate_transition(
    session_id,
    current: CallSessionStatus,
    target: CallSessionStatus,
) -> None:
    if is_terminal(current):
        raise CallSessionTransitionError(
            session_id, current, target, reason=f"{current} is terminal"
        )
    allowed = VALID_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise CallSessionTransitionError(session_id, current, target)
