"""
Workflow retry policy.

Pure, stateless logic. No DB. No side effects.
Caller decides when to persist retry state.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

# Default limits
MAX_RETRIES: int = 3
BASE_BACKOFF_SECONDS: int = 30
MAX_BACKOFF_SECONDS: int = 3600  # 1 hour cap


class RetryExhaustedError(Exception):
    """Raised when retry limit is reached."""

    def __init__(self, attempt: int, max_retries: int) -> None:
        super().__init__(f"Retry limit reached: {attempt}/{max_retries}")
        self.attempt = attempt
        self.max_retries = max_retries


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = MAX_RETRIES
    base_backoff_seconds: int = BASE_BACKOFF_SECONDS
    max_backoff_seconds: int = MAX_BACKOFF_SECONDS
    exponential: bool = True


@dataclass
class RetryState:
    attempt: int = 0
    last_failed_at: datetime | None = None
    last_error: str = ""
    next_retry_at: datetime | None = None


def compute_next_retry(policy: RetryPolicy, state: RetryState) -> datetime:
    """
    Compute next retry timestamp using exponential backoff with cap.
    Raises RetryExhaustedError if limit exceeded.
    """
    if state.attempt >= policy.max_retries:
        raise RetryExhaustedError(state.attempt, policy.max_retries)

    if policy.exponential:
        delay = min(
            policy.base_backoff_seconds * (2 ** state.attempt),
            policy.max_backoff_seconds,
        )
    else:
        delay = policy.base_backoff_seconds

    return datetime.now(UTC) + timedelta(seconds=delay)


def record_failure(
    state: RetryState,
    policy: RetryPolicy,
    error: str,
) -> RetryState:
    """
    Return updated RetryState after a failure.
    Raises RetryExhaustedError if no retries remain.
    """
    new_attempt = state.attempt + 1
    now = datetime.now(UTC)

    if new_attempt > policy.max_retries:
        raise RetryExhaustedError(new_attempt, policy.max_retries)

    # compute next_retry_at for the new attempt index
    if policy.exponential:
        delay = min(
            policy.base_backoff_seconds * (2 ** (new_attempt - 1)),
            policy.max_backoff_seconds,
        )
    else:
        delay = policy.base_backoff_seconds

    return RetryState(
        attempt=new_attempt,
        last_failed_at=now,
        last_error=error,
        next_retry_at=now + timedelta(seconds=delay),
    )


def can_retry(state: RetryState, policy: RetryPolicy) -> bool:
    return state.attempt < policy.max_retries
