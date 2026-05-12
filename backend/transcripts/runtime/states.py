"""Transcript state machine — deterministic transitions only."""
from models.enums import TranscriptStatus

TERMINAL_STATES: frozenset[TranscriptStatus] = frozenset({TranscriptStatus.archived})

VALID_TRANSITIONS: dict[TranscriptStatus, frozenset[TranscriptStatus]] = {
    TranscriptStatus.created: frozenset({
        TranscriptStatus.active,
        TranscriptStatus.failed,
        TranscriptStatus.archived,
    }),
    TranscriptStatus.active: frozenset({
        TranscriptStatus.paused,
        TranscriptStatus.completed,
        TranscriptStatus.failed,
        TranscriptStatus.archived,
    }),
    TranscriptStatus.paused: frozenset({
        TranscriptStatus.active,
        TranscriptStatus.completed,
        TranscriptStatus.failed,
        TranscriptStatus.archived,
    }),
    TranscriptStatus.completed: frozenset({TranscriptStatus.archived}),
    TranscriptStatus.failed: frozenset({
        TranscriptStatus.active,  # recovery
        TranscriptStatus.archived,
    }),
    TranscriptStatus.archived: frozenset(),
}


class TranscriptTransitionError(Exception):
    def __init__(
        self,
        transcript_id,
        from_status: TranscriptStatus,
        to_status: TranscriptStatus,
        reason: str = "",
    ) -> None:
        self.transcript_id = transcript_id
        self.from_status = from_status
        self.to_status = to_status
        msg = f"Transcript {transcript_id}: cannot transition {from_status} -> {to_status}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


def is_terminal(status: TranscriptStatus) -> bool:
    return status in TERMINAL_STATES


def validate_transition(
    transcript_id,
    current: TranscriptStatus,
    target: TranscriptStatus,
) -> None:
    if is_terminal(current):
        raise TranscriptTransitionError(
            transcript_id, current, target, reason=f"{current} is terminal"
        )
    allowed = VALID_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise TranscriptTransitionError(transcript_id, current, target)
