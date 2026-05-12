"""
Phase 5 — Workflow Runtime tests.

Covers: states, transitions, retry policy, recovery replay logic.
No DB required — all unit-level.
"""

import uuid
from datetime import UTC, datetime

import pytest

from models.enums import WorkflowStatus
from workflows.retries import (
    RetryExhaustedError,
    RetryPolicy,
    RetryState,
    can_retry,
    compute_next_retry,
    record_failure,
)
from workflows.states import is_terminal, is_valid_transition
from workflows.transitions import TransitionError, validate_transition

# ---------------------------------------------------------------------------
# states
# ---------------------------------------------------------------------------

class TestStates:
    def test_terminal_states(self):
        assert is_terminal(WorkflowStatus.completed)
        assert is_terminal(WorkflowStatus.failed)
        assert is_terminal(WorkflowStatus.cancelled)

    def test_non_terminal_states(self):
        assert not is_terminal(WorkflowStatus.pending)
        assert not is_terminal(WorkflowStatus.active)
        assert not is_terminal(WorkflowStatus.paused)

    def test_valid_transitions_from_pending(self):
        assert is_valid_transition(WorkflowStatus.pending, WorkflowStatus.active)
        assert is_valid_transition(WorkflowStatus.pending, WorkflowStatus.cancelled)

    def test_invalid_transitions_from_pending(self):
        assert not is_valid_transition(WorkflowStatus.pending, WorkflowStatus.completed)
        assert not is_valid_transition(WorkflowStatus.pending, WorkflowStatus.paused)
        assert not is_valid_transition(WorkflowStatus.pending, WorkflowStatus.failed)

    def test_valid_transitions_from_active(self):
        for target in (
            WorkflowStatus.paused,
            WorkflowStatus.completed,
            WorkflowStatus.failed,
            WorkflowStatus.cancelled,
        ):
            assert is_valid_transition(WorkflowStatus.active, target)

    def test_invalid_transitions_from_active(self):
        assert not is_valid_transition(WorkflowStatus.active, WorkflowStatus.pending)

    def test_no_transitions_from_terminal(self):
        for terminal in (WorkflowStatus.completed, WorkflowStatus.failed, WorkflowStatus.cancelled):
            for target in WorkflowStatus:
                assert not is_valid_transition(terminal, target)

    def test_paused_can_resume_or_cancel(self):
        assert is_valid_transition(WorkflowStatus.paused, WorkflowStatus.active)
        assert is_valid_transition(WorkflowStatus.paused, WorkflowStatus.cancelled)
        assert not is_valid_transition(WorkflowStatus.paused, WorkflowStatus.completed)


# ---------------------------------------------------------------------------
# transitions
# ---------------------------------------------------------------------------

class TestTransitions:
    def setup_method(self):
        self.wid = uuid.uuid4()

    def test_valid_transition_returns_result(self):
        result = validate_transition(self.wid, WorkflowStatus.pending, WorkflowStatus.active)
        assert result.from_status == WorkflowStatus.pending
        assert result.to_status == WorkflowStatus.active
        assert result.workflow_id == self.wid

    def test_terminal_raises(self):
        with pytest.raises(TransitionError) as exc_info:
            validate_transition(self.wid, WorkflowStatus.completed, WorkflowStatus.active)
        assert "terminal" in str(exc_info.value)

    def test_invalid_transition_raises(self):
        with pytest.raises(TransitionError):
            validate_transition(self.wid, WorkflowStatus.pending, WorkflowStatus.completed)

    def test_error_includes_workflow_id(self):
        with pytest.raises(TransitionError) as exc_info:
            validate_transition(self.wid, WorkflowStatus.failed, WorkflowStatus.active)
        assert str(self.wid) in str(exc_info.value)

    def test_all_valid_transitions_succeed(self):
        valid_pairs = [
            (WorkflowStatus.pending, WorkflowStatus.active),
            (WorkflowStatus.pending, WorkflowStatus.cancelled),
            (WorkflowStatus.active, WorkflowStatus.paused),
            (WorkflowStatus.active, WorkflowStatus.completed),
            (WorkflowStatus.active, WorkflowStatus.failed),
            (WorkflowStatus.active, WorkflowStatus.cancelled),
            (WorkflowStatus.paused, WorkflowStatus.active),
            (WorkflowStatus.paused, WorkflowStatus.cancelled),
        ]
        for from_s, to_s in valid_pairs:
            result = validate_transition(self.wid, from_s, to_s)
            assert result.to_status == to_s


# ---------------------------------------------------------------------------
# retries
# ---------------------------------------------------------------------------

class TestRetries:
    def setup_method(self):
        self.policy = RetryPolicy(max_retries=3, base_backoff_seconds=10)

    def test_can_retry_fresh(self):
        assert can_retry(RetryState(), self.policy)

    def test_cannot_retry_at_limit(self):
        state = RetryState(attempt=3)
        assert not can_retry(state, self.policy)

    def test_record_failure_increments_attempt(self):
        state = RetryState()
        state = record_failure(state, self.policy, "timeout")
        assert state.attempt == 1
        assert state.last_error == "timeout"

    def test_record_failure_sets_next_retry(self):
        state = RetryState()
        state = record_failure(state, self.policy, "error")
        assert state.next_retry_at is not None
        assert state.next_retry_at > datetime.now(UTC)

    def test_record_failure_exhaust_raises(self):
        state = RetryState(attempt=3)
        with pytest.raises(RetryExhaustedError) as exc_info:
            record_failure(state, self.policy, "error")
        assert exc_info.value.max_retries == 3

    def test_backoff_grows_exponential(self):
        t0 = compute_next_retry(self.policy, RetryState(attempt=0))
        t1 = compute_next_retry(self.policy, RetryState(attempt=1))
        t2 = compute_next_retry(self.policy, RetryState(attempt=2))
        assert t1 > t0
        assert t2 > t1

    def test_backoff_capped(self):
        capped_policy = RetryPolicy(
            max_retries=20,
            base_backoff_seconds=10,
            max_backoff_seconds=60,
        )
        # high attempt — should be capped
        t_high = compute_next_retry(capped_policy, RetryState(attempt=10))
        # high attempt should still be within max_backoff ceiling
        from datetime import timedelta
        ceiling = datetime.now(UTC) + timedelta(seconds=61)
        assert t_high < ceiling

    def test_linear_backoff(self):
        linear = RetryPolicy(max_retries=3, base_backoff_seconds=30, exponential=False)
        t0 = compute_next_retry(linear, RetryState(attempt=0))
        t1 = compute_next_retry(linear, RetryState(attempt=1))
        # linear: both ~30s from now, so very close
        delta = abs((t1 - t0).total_seconds())
        assert delta < 2  # within 2s of each other


# ---------------------------------------------------------------------------
# recovery replay (pure logic — no DB)
# ---------------------------------------------------------------------------

class TestRecoveryReplayLogic:
    """Test the _STATUS_EVENTS mapping used by replay (no DB needed)."""

    def test_status_event_map_complete(self):
        from workflows.recovery import _STATUS_EVENTS

        expected = {
            "workflow.started",
            "workflow.paused",
            "workflow.resumed",
            "workflow.completed",
            "workflow.failed",
            "workflow.cancelled",
        }
        assert expected == set(_STATUS_EVENTS.keys())

    def test_started_maps_to_active(self):
        from workflows.recovery import _STATUS_EVENTS
        assert _STATUS_EVENTS["workflow.started"] == WorkflowStatus.active

    def test_terminal_events_map_correctly(self):
        from workflows.recovery import _STATUS_EVENTS
        assert _STATUS_EVENTS["workflow.completed"] == WorkflowStatus.completed
        assert _STATUS_EVENTS["workflow.failed"] == WorkflowStatus.failed
        assert _STATUS_EVENTS["workflow.cancelled"] == WorkflowStatus.cancelled
