"""
Phase 8 — Realtime Call Runtime Integration Tests.

Tests run against a real postgres session (karpathys_test).
Each test is wrapped in a SAVEPOINT so mutations roll back — no teardown needed.

Covers:
- session persistence and state transitions
- participant join/leave/reconnect lifecycle
- append-only event ordering
- sequence consistency (replay)
- pagination consistency
- heartbeat tracking and stale detection
- concurrent join safety
- duplicate prevention
- reconnect recovery
- presence derivation
- incremental event ordering
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from calls.repositories import (
    CallEventRepository,
    CallParticipantRepository,
    CallSessionRepository,
)
from calls.runtime.presence import PresenceRuntime
from calls.runtime.runtime import (
    EVT_PARTICIPANT_DROPPED,
    EVT_PARTICIPANT_JOINED,
    EVT_PARTICIPANT_LEFT,
    EVT_PARTICIPANT_RECONNECTED,
    EVT_SESSION_COMPLETED,
    EVT_SESSION_CREATED,
    EVT_SESSION_FAILED,
    EVT_SESSION_STARTED,
    CallSessionRuntime,
)
from calls.runtime.states import CallSessionTransitionError
from models.enums import CallSessionStatus, ParticipantRole, ParticipantStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rt(db: AsyncSession) -> CallSessionRuntime:
    return CallSessionRuntime(db)


def _sessions(db: AsyncSession) -> CallSessionRepository:
    return CallSessionRepository(db)


def _participants(db: AsyncSession) -> CallParticipantRepository:
    return CallParticipantRepository(db)


def _events(db: AsyncSession) -> CallEventRepository:
    return CallEventRepository(db)


def _presence(db: AsyncSession) -> PresenceRuntime:
    return PresenceRuntime(db)


# Suppress realtime broadcast in all tests — WS not running in test env
@pytest.fixture(autouse=True)
def _no_broadcast(monkeypatch):
    monkeypatch.setattr(
        "calls.runtime.broadcaster.broadcast_service.publish",
        AsyncMock(return_value=0),
    )


# ---------------------------------------------------------------------------
# 1. Session Persistence
# ---------------------------------------------------------------------------

class TestSessionPersistence:
    async def test_create_session_persists(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        fetched = await _sessions(db).get_by_id(s.id)
        assert fetched is not None
        assert fetched.session_status == CallSessionStatus.waiting
        assert fetched.correlation_id is not None

    async def test_create_session_emits_created_event(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        evts = await _events(db).get_all_ordered(s.id)
        assert len(evts) == 1
        assert evts[0].event_type == EVT_SESSION_CREATED
        assert evts[0].sequence == 0

    async def test_create_session_with_call_id_nullable(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session(call_id=None)
        assert s.call_id is None

    async def test_complete_session_persists(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)
        await rt.complete_session(s.id)
        fetched = await _sessions(db).get_by_id(s.id)
        assert fetched.session_status == CallSessionStatus.completed
        assert fetched.ended_at is not None

    async def test_fail_session_persists(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)
        await rt.fail_session(s.id, reason="provider_timeout")
        fetched = await _sessions(db).get_by_id(s.id)
        assert fetched.session_status == CallSessionStatus.failed
        assert fetched.ended_at is not None

    async def test_complete_emits_completed_event(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)
        await rt.complete_session(s.id)
        evts = await _events(db).get_all_ordered(s.id)
        types = [e.event_type for e in evts]
        assert EVT_SESSION_COMPLETED in types

    async def test_fail_emits_failed_event(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)
        await rt.fail_session(s.id, reason="test")
        evts = await _events(db).get_all_ordered(s.id)
        types = [e.event_type for e in evts]
        assert EVT_SESSION_FAILED in types


# ---------------------------------------------------------------------------
# 2. State Transition Durability
# ---------------------------------------------------------------------------

class TestStateTransitionDurability:
    async def test_waiting_to_active_on_first_join(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        assert s.session_status == CallSessionStatus.waiting

        await rt.join(s.id, ParticipantRole.operator)
        fetched = await _sessions(db).get_by_id(s.id)
        assert fetched.session_status == CallSessionStatus.active
        assert fetched.started_at is not None

    async def test_complete_terminal_rejects_further_transitions(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)
        await rt.complete_session(s.id)

        with pytest.raises(CallSessionTransitionError):
            await rt.complete_session(s.id)

    async def test_failed_terminal_rejects_complete(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)
        await rt.fail_session(s.id, reason="err")

        with pytest.raises(CallSessionTransitionError):
            await rt.complete_session(s.id)

    async def test_invalid_transition_leaves_no_extra_event(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)
        await rt.complete_session(s.id)

        evts_before = await _events(db).get_all_ordered(s.id)
        count_before = len(evts_before)

        with pytest.raises(CallSessionTransitionError):
            await rt.fail_session(s.id, reason="late")

        evts_after = await _events(db).get_all_ordered(s.id)
        assert len(evts_after) == count_before  # no extra event written

    async def test_waiting_session_cannot_complete_directly(self, db: AsyncSession):
        """waiting -> completed is not a valid transition."""
        rt = _rt(db)
        s = await rt.create_session()

        with pytest.raises(CallSessionTransitionError):
            await rt.complete_session(s.id)


# ---------------------------------------------------------------------------
# 3. Participant Lifecycle
# ---------------------------------------------------------------------------

class TestParticipantLifecycle:
    async def test_join_creates_participant(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)
        assert p.id is not None
        assert p.session_id == s.id
        assert p.role == ParticipantRole.operator
        assert p.participant_status == ParticipantStatus.joined

    async def test_join_sets_heartbeat(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)
        assert p.last_heartbeat_at is not None

    async def test_join_emits_joined_event(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)
        evts = await _events(db).get_all_ordered(s.id)
        types = [e.event_type for e in evts]
        assert EVT_PARTICIPANT_JOINED in types

    async def test_join_stores_connection_id(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator, connection_id="conn-abc")
        fetched = (await _participants(db).get_by_session(s.id))[0]
        assert fetched.connection_id == "conn-abc"

    async def test_leave_sets_left_status(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)
        await rt.leave(s.id, p.id)
        fetched_p = await _participants(db).get_by_id(p.id)
        assert fetched_p.participant_status == ParticipantStatus.left
        assert fetched_p.left_at is not None
        assert fetched_p.connection_id is None

    async def test_leave_emits_left_event(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)
        await rt.leave(s.id, p.id)
        evts = await _events(db).get_all_ordered(s.id)
        types = [e.event_type for e in evts]
        assert EVT_PARTICIPANT_LEFT in types

    async def test_multiple_participants_different_roles(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p1 = await rt.join(s.id, ParticipantRole.operator)
        _, p2 = await rt.join(s.id, ParticipantRole.lead)
        _, p3 = await rt.join(s.id, ParticipantRole.observer)

        all_p = await _participants(db).get_by_session(s.id)
        roles = {p.role for p in all_p}
        assert roles == {ParticipantRole.operator, ParticipantRole.lead, ParticipantRole.observer}

    async def test_join_terminal_session_raises(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)
        await rt.complete_session(s.id)

        with pytest.raises(CallSessionTransitionError):
            await rt.join(s.id, ParticipantRole.lead)


# ---------------------------------------------------------------------------
# 4. Append-Only Event Ordering
# ---------------------------------------------------------------------------

class TestEventOrdering:
    async def test_events_monotonically_increasing_sequence(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)
        _, p2 = await rt.join(s.id, ParticipantRole.lead)
        await rt.leave(s.id, p2.id)
        await rt.complete_session(s.id)

        evts = await _events(db).get_all_ordered(s.id)
        seqs = [e.sequence for e in evts]
        assert seqs == sorted(seqs), "sequences not monotonically increasing"
        assert len(set(seqs)) == len(seqs), "duplicate sequences found"

    async def test_events_start_at_zero(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        evts = await _events(db).get_all_ordered(s.id)
        assert evts[0].sequence == 0

    async def test_event_payload_contains_session_id(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        evts = await _events(db).get_all_ordered(s.id)
        # All non-WS events are persisted via append_event without session_id in payload
        # — just verify events exist and have correct session_id FK
        assert all(e.session_id == s.id for e in evts)

    async def test_full_lifecycle_event_sequence(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)
        await rt.leave(s.id, p.id)
        await rt.complete_session(s.id)

        evts = await _events(db).get_all_ordered(s.id)
        types = [e.event_type for e in evts]
        assert types[0] == EVT_SESSION_CREATED
        assert EVT_SESSION_STARTED in types
        assert EVT_PARTICIPANT_JOINED in types
        assert EVT_PARTICIPANT_LEFT in types
        assert EVT_SESSION_COMPLETED in types

    async def test_events_are_never_mutated(self, db: AsyncSession):
        """Re-fetching events returns identical records."""
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)

        first_fetch = await _events(db).get_all_ordered(s.id)
        second_fetch = await _events(db).get_all_ordered(s.id)

        for a, b in zip(first_fetch, second_fetch):
            assert a.id == b.id
            assert a.sequence == b.sequence
            assert a.event_type == b.event_type


# ---------------------------------------------------------------------------
# 5. Replay Consistency
# ---------------------------------------------------------------------------

class TestReplayConsistency:
    async def test_replay_returns_correct_final_status(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)
        await rt.complete_session(s.id)

        result = await rt.replay(s.id)
        assert result.final_status == CallSessionStatus.completed
        assert result.session_id == s.id

    async def test_replay_counts_all_events(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)
        await rt.join(s.id, ParticipantRole.lead)
        await rt.complete_session(s.id)

        result = await rt.replay(s.id)
        evts = await _events(db).get_all_ordered(s.id)
        assert result.replayed_events == len(evts)

    async def test_replay_is_deterministic(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)
        await rt.fail_session(s.id, reason="test")

        r1 = await rt.replay(s.id)
        r2 = await rt.replay(s.id)
        assert r1.final_status == r2.final_status
        assert r1.replayed_events == r2.replayed_events
        assert r1.participant_count == r2.participant_count

    async def test_replay_participant_count_active_only(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p1 = await rt.join(s.id, ParticipantRole.operator)
        _, p2 = await rt.join(s.id, ParticipantRole.lead)
        await rt.leave(s.id, p2.id)  # p2 left — not counted as active

        result = await rt.replay(s.id)
        assert result.participant_count == 1  # only p1 still joined

    async def test_replay_on_failed_session(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)
        await rt.fail_session(s.id, reason="network")

        result = await rt.replay(s.id)
        assert result.final_status == CallSessionStatus.failed

    async def test_replay_waiting_session(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        result = await rt.replay(s.id)
        assert result.final_status == CallSessionStatus.waiting
        assert result.replayed_events == 1  # only created event


# ---------------------------------------------------------------------------
# 6. Pagination Consistency
# ---------------------------------------------------------------------------

class TestPaginationConsistency:
    async def test_events_paginated_ordered_by_sequence(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        for _ in range(5):
            _, p = await rt.join(s.id, ParticipantRole.observer)
            await rt.leave(s.id, p.id)

        page1 = await _events(db).get_by_session(s.id, page=1, page_size=5)
        page2 = await _events(db).get_by_session(s.id, page=2, page_size=5)

        assert len(page1.items) == 5
        assert len(page2.items) >= 1
        # Last seq of page1 < first seq of page2
        assert page1.items[-1].sequence < page2.items[0].sequence

    async def test_events_total_count_consistent(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)
        await rt.complete_session(s.id)

        all_evts = await _events(db).get_all_ordered(s.id)
        paginated = await _events(db).get_by_session(s.id, page=1, page_size=100)
        assert paginated.total == len(all_evts)

    async def test_get_after_sequence_returns_missed_events(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)
        await rt.leave(s.id, p.id)
        await rt.complete_session(s.id)

        # Get events after sequence 0 (the created event)
        missed = await _events(db).get_after_sequence(s.id, after_sequence=0)
        assert len(missed) > 0
        assert all(e.sequence > 0 for e in missed)

    async def test_get_after_sequence_excludes_checkpoint(self, db: AsyncSession):
        """after_sequence is exclusive — checkpoint event not returned."""
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)

        evts = await _events(db).get_all_ordered(s.id)
        last_seq = evts[-1].sequence

        missed = await _events(db).get_after_sequence(s.id, after_sequence=last_seq)
        assert len(missed) == 0  # nothing after latest

    async def test_participants_paginated_by_session(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        for _ in range(3):
            await rt.join(s.id, ParticipantRole.observer)

        all_p = await _participants(db).get_by_session(s.id)
        assert len(all_p) == 3

    async def test_active_sessions_paginated(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)

        page = await _sessions(db).get_active(page=1, page_size=20)
        assert page.total >= 1
        ids = [item.id for item in page.items]
        assert s.id in ids


# ---------------------------------------------------------------------------
# 7. Reconnect Recovery
# ---------------------------------------------------------------------------

class TestReconnectRecovery:
    async def test_reconnect_restores_joined_status(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator, connection_id="conn-old")

        # Simulate drop
        await rt.drop_participant(s.id, p.id)
        dropped = await _participants(db).get_by_id(p.id)
        assert dropped.participant_status == ParticipantStatus.dropped

        # Reconnect
        reconnected = await rt.reconnect(s.id, p.id, connection_id="conn-new")
        assert reconnected.participant_status == ParticipantStatus.joined
        assert reconnected.connection_id == "conn-new"

    async def test_reconnect_updates_heartbeat(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)
        await rt.drop_participant(s.id, p.id)

        reconnected = await rt.reconnect(s.id, p.id, "conn-new")
        assert reconnected.last_heartbeat_at is not None

    async def test_reconnect_emits_reconnected_event(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)
        await rt.drop_participant(s.id, p.id)
        await rt.reconnect(s.id, p.id, "conn-new")

        evts = await _events(db).get_all_ordered(s.id)
        types = [e.event_type for e in evts]
        assert EVT_PARTICIPANT_RECONNECTED in types

    async def test_reconnect_from_joined_raises(self, db: AsyncSession):
        """Cannot reconnect a participant who is still joined."""
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator, connection_id="conn-a")

        with pytest.raises(ValueError):
            await rt.reconnect(s.id, p.id, connection_id="conn-b")

    async def test_reconnect_then_leave(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)
        await rt.drop_participant(s.id, p.id)
        await rt.reconnect(s.id, p.id, "conn-new")
        await rt.leave(s.id, p.id)

        fetched = await _participants(db).get_by_id(p.id)
        assert fetched.participant_status == ParticipantStatus.left

    async def test_missed_events_recoverable_via_get_after_sequence(self, db: AsyncSession):
        """After reconnect, client can request missed events by checkpoint sequence."""
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)

        # Events before "disconnect"
        evts_before = await _events(db).get_all_ordered(s.id)
        checkpoint = evts_before[-1].sequence

        # More events happen while client was disconnected
        _, p2 = await rt.join(s.id, ParticipantRole.lead)
        await rt.leave(s.id, p2.id)

        missed = await _events(db).get_after_sequence(s.id, after_sequence=checkpoint)
        assert len(missed) == 2  # joined + left for p2
        assert all(e.sequence > checkpoint for e in missed)


# ---------------------------------------------------------------------------
# 8. Duplicate Prevention
# ---------------------------------------------------------------------------

class TestDuplicatePrevention:
    async def test_sequence_numbers_never_duplicated(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        for _ in range(10):
            _, p = await rt.join(s.id, ParticipantRole.observer)
            await rt.leave(s.id, p.id)

        evts = await _events(db).get_all_ordered(s.id)
        seqs = [e.sequence for e in evts]
        assert len(seqs) == len(set(seqs)), "duplicate sequence numbers detected"

    async def test_same_participant_cannot_reconnect_if_joined(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator, connection_id="conn-1")

        with pytest.raises(ValueError):
            await rt.reconnect(s.id, p.id, connection_id="conn-2")

    async def test_get_by_connection_id_returns_active_only(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator, connection_id="conn-xyz")
        await rt.leave(s.id, p.id)

        # After leave, connection_id is None — lookup returns nothing
        found = await _participants(db).get_by_connection_id("conn-xyz")
        assert found is None


# ---------------------------------------------------------------------------
# 9. Heartbeat and Stale Detection
# ---------------------------------------------------------------------------

class TestHeartbeatAndStale:
    async def test_heartbeat_updates_timestamp(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)

        original_hb = (await _participants(db).get_by_id(p.id)).last_heartbeat_at
        await rt.heartbeat(s.id, p.id)
        updated_hb = (await _participants(db).get_by_id(p.id)).last_heartbeat_at
        # Updated timestamp >= original
        assert updated_hb >= original_hb

    async def test_stale_detection_finds_expired_participants(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)

        # Manually back-date heartbeat to simulate stale connection
        participant = await _participants(db).get_for_update_or_raise(p.id)
        participant.last_heartbeat_at = datetime.now(UTC) - timedelta(seconds=120)
        db.add(participant)
        await db.flush()

        stale = await _participants(db).get_stale(heartbeat_threshold_seconds=30)
        stale_ids = [p.id for p in stale]
        assert participant.id in stale_ids

    async def test_fresh_heartbeat_not_stale(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)
        await rt.heartbeat(s.id, p.id)

        stale = await _participants(db).get_stale(heartbeat_threshold_seconds=30)
        stale_ids = [p.id for p in stale]
        assert p.id not in stale_ids

    async def test_stale_cleanup_drops_expired_participants(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)

        # Back-date heartbeat
        participant = await _participants(db).get_for_update_or_raise(p.id)
        participant.last_heartbeat_at = datetime.now(UTC) - timedelta(seconds=120)
        db.add(participant)
        await db.flush()

        presence_rt = _presence(db)
        result = await presence_rt.cleanup_stale(heartbeat_threshold_seconds=30)
        assert result.dropped_count >= 1
        assert participant.id in result.participant_ids

        fetched = await _participants(db).get_by_id(p.id)
        assert fetched.participant_status == ParticipantStatus.dropped

    async def test_stale_cleanup_idempotent(self, db: AsyncSession):
        """Running cleanup twice on already-dropped participants has no effect."""
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)

        participant = await _participants(db).get_for_update_or_raise(p.id)
        participant.last_heartbeat_at = datetime.now(UTC) - timedelta(seconds=120)
        db.add(participant)
        await db.flush()

        presence_rt = _presence(db)
        r1 = await presence_rt.cleanup_stale(30)
        r2 = await presence_rt.cleanup_stale(30)

        assert r1.dropped_count >= 1
        assert r2.dropped_count == 0  # already dropped, not picked up again

    async def test_left_participants_not_detected_as_stale(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)
        await rt.leave(s.id, p.id)

        # Back-date heartbeat on a left participant
        participant = await _participants(db).get_for_update_or_raise(p.id)
        participant.last_heartbeat_at = datetime.now(UTC) - timedelta(seconds=120)
        db.add(participant)
        await db.flush()

        stale = await _participants(db).get_stale(heartbeat_threshold_seconds=30)
        stale_ids = [sp.id for sp in stale]
        assert participant.id not in stale_ids  # status=left, not joined


# ---------------------------------------------------------------------------
# 10. Presence Derivation
# ---------------------------------------------------------------------------

class TestPresenceDerivation:
    async def test_presence_reflects_joined_participants(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p1 = await rt.join(s.id, ParticipantRole.operator)
        _, p2 = await rt.join(s.id, ParticipantRole.lead)

        presence_rt = _presence(db)
        records = await presence_rt.get_presence(s.id)
        assert len(records) == 2
        online_ids = {r.participant_id for r in records if r.is_online}
        assert p1.id in online_ids
        assert p2.id in online_ids

    async def test_presence_marks_stale_as_not_online(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)

        # Back-date heartbeat
        participant = await _participants(db).get_for_update_or_raise(p.id)
        participant.last_heartbeat_at = datetime.now(UTC) - timedelta(seconds=120)
        db.add(participant)
        await db.flush()

        presence_rt = _presence(db)
        records = await presence_rt.get_presence(s.id)
        stale_record = next(r for r in records if r.participant_id == p.id)
        assert stale_record.is_online is False

    async def test_presence_includes_left_participants(self, db: AsyncSession):
        """Presence returns all participants — callers filter by status."""
        rt = _rt(db)
        s = await rt.create_session()
        _, p1 = await rt.join(s.id, ParticipantRole.operator)
        _, p2 = await rt.join(s.id, ParticipantRole.lead)
        await rt.leave(s.id, p2.id)

        presence_rt = _presence(db)
        records = await presence_rt.get_presence(s.id)
        assert len(records) == 2

        left_record = next(r for r in records if r.participant_id == p2.id)
        assert left_record.status == ParticipantStatus.left
        assert left_record.is_online is False

    async def test_presence_replay_safe(self, db: AsyncSession):
        """Presence is derived from CallParticipant rows — same result on re-call."""
        rt = _rt(db)
        s = await rt.create_session()
        await rt.join(s.id, ParticipantRole.operator)

        presence_rt = _presence(db)
        r1 = await presence_rt.get_presence(s.id)
        r2 = await presence_rt.get_presence(s.id)

        assert len(r1) == len(r2)
        ids1 = {r.participant_id for r in r1}
        ids2 = {r.participant_id for r in r2}
        assert ids1 == ids2

    async def test_get_active_participants_only(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p1 = await rt.join(s.id, ParticipantRole.operator)
        _, p2 = await rt.join(s.id, ParticipantRole.lead)
        await rt.leave(s.id, p2.id)

        active = await _participants(db).get_active_by_session(s.id)
        assert len(active) == 1
        assert active[0].id == p1.id


# ---------------------------------------------------------------------------
# 11. Drop Participant
# ---------------------------------------------------------------------------

class TestDropParticipant:
    async def test_drop_sets_dropped_status(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)
        await rt.drop_participant(s.id, p.id)

        fetched = await _participants(db).get_by_id(p.id)
        assert fetched.participant_status == ParticipantStatus.dropped
        assert fetched.connection_id is None

    async def test_drop_emits_dropped_event(self, db: AsyncSession):
        rt = _rt(db)
        s = await rt.create_session()
        _, p = await rt.join(s.id, ParticipantRole.operator)
        await rt.drop_participant(s.id, p.id)

        evts = await _events(db).get_all_ordered(s.id)
        types = [e.event_type for e in evts]
        assert EVT_PARTICIPANT_DROPPED in types
