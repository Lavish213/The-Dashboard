"""
Transcript runtime unit tests — no DB required.
Tests: state machine, transitions, replay logic.
"""
import uuid

import pytest

from models.enums import TranscriptStatus
from transcripts.runtime.runtime import _STATUS_EVENTS, EVT_TRANSCRIPT_CHUNK_ADDED
from transcripts.runtime.states import (
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    TranscriptTransitionError,
    is_terminal,
    validate_transition,
)


class TestTranscriptStates:
    def test_archived_is_only_terminal(self):
        assert TranscriptStatus.archived in TERMINAL_STATES
        assert len(TERMINAL_STATES) == 1

    def test_active_statuses_not_terminal(self):
        for s in [
            TranscriptStatus.created,
            TranscriptStatus.active,
            TranscriptStatus.paused,
            TranscriptStatus.completed,
            TranscriptStatus.failed,
        ]:
            assert not is_terminal(s)

    def test_created_can_start(self):
        assert TranscriptStatus.active in VALID_TRANSITIONS[TranscriptStatus.created]

    def test_active_can_pause_complete_fail_archive(self):
        allowed = VALID_TRANSITIONS[TranscriptStatus.active]
        assert TranscriptStatus.paused in allowed
        assert TranscriptStatus.completed in allowed
        assert TranscriptStatus.failed in allowed
        assert TranscriptStatus.archived in allowed

    def test_paused_can_resume(self):
        assert TranscriptStatus.active in VALID_TRANSITIONS[TranscriptStatus.paused]

    def test_completed_can_only_archive(self):
        assert VALID_TRANSITIONS[TranscriptStatus.completed] == frozenset({TranscriptStatus.archived})

    def test_failed_can_recover_or_archive(self):
        allowed = VALID_TRANSITIONS[TranscriptStatus.failed]
        assert TranscriptStatus.active in allowed
        assert TranscriptStatus.archived in allowed

    def test_archived_has_no_transitions(self):
        assert VALID_TRANSITIONS[TranscriptStatus.archived] == frozenset()


class TestTranscriptTransitions:
    def test_valid_transition_does_not_raise(self):
        tid = uuid.uuid4()
        validate_transition(tid, TranscriptStatus.created, TranscriptStatus.active)

    def test_invalid_transition_raises(self):
        tid = uuid.uuid4()
        with pytest.raises(TranscriptTransitionError):
            validate_transition(tid, TranscriptStatus.completed, TranscriptStatus.active)

    def test_terminal_transition_raises(self):
        tid = uuid.uuid4()
        with pytest.raises(TranscriptTransitionError) as exc_info:
            validate_transition(tid, TranscriptStatus.archived, TranscriptStatus.active)
        assert "terminal" in str(exc_info.value)

    def test_error_includes_workflow_id(self):
        tid = uuid.uuid4()
        with pytest.raises(TranscriptTransitionError) as exc_info:
            validate_transition(tid, TranscriptStatus.completed, TranscriptStatus.paused)
        assert str(tid) in str(exc_info.value)

    def test_all_valid_transitions_pass(self):
        tid = uuid.uuid4()
        for from_status, targets in VALID_TRANSITIONS.items():
            for target in targets:
                validate_transition(tid, from_status, target)


class TestReplayStatusEvents:
    def test_all_lifecycle_events_mapped(self):
        expected = {
            "transcript.created",
            "transcript.started",
            "transcript.paused",
            "transcript.resumed",
            "transcript.completed",
            "transcript.failed",
            "transcript.archived",
        }
        assert expected <= set(_STATUS_EVENTS.keys())

    def test_chunk_added_not_in_status_events(self):
        assert EVT_TRANSCRIPT_CHUNK_ADDED not in _STATUS_EVENTS

    def test_started_maps_to_active(self):
        assert _STATUS_EVENTS["transcript.started"] == TranscriptStatus.active

    def test_archived_maps_to_archived(self):
        assert _STATUS_EVENTS["transcript.archived"] == TranscriptStatus.archived
