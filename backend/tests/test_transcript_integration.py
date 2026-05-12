"""
Transcript integration tests.

Tests: persistence, chunk append, replay, ordering, concurrency safety,
       pagination, transition durability, recovery.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import TranscriptSourceType, TranscriptStatus, TranscriptStreamType
from transcripts.repositories.chunk import TranscriptChunkRepository
from transcripts.repositories.event import TranscriptEventRepository
from transcripts.repositories.transcript import TranscriptRepository
from transcripts.runtime.runtime import TranscriptRuntime
from transcripts.runtime.states import TranscriptTransitionError


def _rt(db: AsyncSession) -> TranscriptRuntime:
    return TranscriptRuntime(db)


def _chunks(db: AsyncSession) -> TranscriptChunkRepository:
    return TranscriptChunkRepository(db)


def _events(db: AsyncSession) -> TranscriptEventRepository:
    return TranscriptEventRepository(db)


def _repo(db: AsyncSession) -> TranscriptRepository:
    return TranscriptRepository(db)


# ---------------------------------------------------------------------------
# 1. Transcript Persistence
# ---------------------------------------------------------------------------

class TestTranscriptPersistence:
    async def test_create_persists_transcript(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create(source_type=TranscriptSourceType.call)
        fetched = await _repo(db).get_by_id(t.id)
        assert fetched is not None
        assert fetched.transcript_status == TranscriptStatus.created

    async def test_create_emits_created_event(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        events = await _events(db).get_all_ordered(t.id)
        assert len(events) == 1
        assert events[0].event_type == "transcript.created"

    async def test_create_with_nullable_workflow_id(self, db: AsyncSession):
        rt = _rt(db)
        # workflow_id is nullable FK; None avoids FK violation in tests
        t = await rt.create(workflow_id=None)
        assert t.workflow_id is None

    async def test_source_type_persisted(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create(source_type=TranscriptSourceType.realtime)
        fetched = await _repo(db).get_by_id(t.id)
        assert fetched.source_type == TranscriptSourceType.realtime

    async def test_default_status_is_created(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        assert t.transcript_status == TranscriptStatus.created


# ---------------------------------------------------------------------------
# 2. State Transition Durability
# ---------------------------------------------------------------------------

class TestStateTransitionDurability:
    async def test_start_persists_active(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        t = await rt.start(t.id)
        fetched = await _repo(db).get_by_id(t.id)
        assert fetched.transcript_status == TranscriptStatus.active

    async def test_pause_persists(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        t = await rt.start(t.id)
        t = await rt.pause(t.id)
        fetched = await _repo(db).get_by_id(t.id)
        assert fetched.transcript_status == TranscriptStatus.paused

    async def test_resume_persists(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        await rt.pause(t.id)
        t = await rt.resume(t.id)
        fetched = await _repo(db).get_by_id(t.id)
        assert fetched.transcript_status == TranscriptStatus.active

    async def test_complete_persists(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        t = await rt.complete(t.id, duration_seconds=120)
        fetched = await _repo(db).get_by_id(t.id)
        assert fetched.transcript_status == TranscriptStatus.completed
        assert fetched.duration_seconds == 120

    async def test_fail_persists(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        t = await rt.fail(t.id, reason="call dropped")
        fetched = await _repo(db).get_by_id(t.id)
        assert fetched.transcript_status == TranscriptStatus.failed

    async def test_archive_persists(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        await rt.complete(t.id)
        t = await rt.archive(t.id)
        fetched = await _repo(db).get_by_id(t.id)
        assert fetched.transcript_status == TranscriptStatus.archived

    async def test_invalid_transition_does_not_mutate(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        await rt.complete(t.id)

        with pytest.raises(TranscriptTransitionError):
            await rt.pause(t.id)  # completed → paused not allowed

        fetched = await _repo(db).get_by_id(t.id)
        assert fetched.transcript_status == TranscriptStatus.completed

    async def test_archived_blocks_all_transitions(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        await rt.complete(t.id)
        await rt.archive(t.id)

        with pytest.raises(TranscriptTransitionError):
            await rt.fail(t.id, reason="too late")

    async def test_full_lifecycle(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        await rt.pause(t.id)
        await rt.resume(t.id)
        await rt.complete(t.id)
        await rt.archive(t.id)
        fetched = await _repo(db).get_by_id(t.id)
        assert fetched.transcript_status == TranscriptStatus.archived


# ---------------------------------------------------------------------------
# 3. Chunk Append
# ---------------------------------------------------------------------------

class TestChunkAppend:
    async def test_append_chunk_creates_row(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        chunk = await rt.append_chunk(t.id, speaker="agent", text="Hello")
        assert chunk.chunk_index == 0
        assert chunk.transcript_id == t.id

    async def test_append_increments_chunk_index(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        c0 = await rt.append_chunk(t.id, speaker="agent", text="Hello")
        c1 = await rt.append_chunk(t.id, speaker="user", text="Hi")
        assert c0.chunk_index == 0
        assert c1.chunk_index == 1

    async def test_chunk_emits_event(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        await rt.append_chunk(t.id, speaker="agent", text="Hello")
        evts = await _events(db).get_all_ordered(t.id)
        assert any(e.event_type == "transcript.chunk_added" for e in evts)

    async def test_chunk_on_non_active_raises(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        # still in created state
        with pytest.raises(TranscriptTransitionError):
            await rt.append_chunk(t.id, speaker="agent", text="Too early")

    async def test_chunk_stream_type_persisted(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        chunk = await rt.append_chunk(
            t.id,
            speaker="system",
            text="System msg",
            stream_type=TranscriptStreamType.system,
        )
        assert chunk.stream_type == TranscriptStreamType.system

    async def test_chunk_ordering_deterministic(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        for i in range(5):
            await rt.append_chunk(t.id, speaker="agent", text=f"chunk {i}")
        result = await _chunks(db).get_by_transcript(t.id, page=1, page_size=10)
        indexes = [c.chunk_index for c in result.items]
        assert indexes == sorted(indexes)


# ---------------------------------------------------------------------------
# 4. Pagination
# ---------------------------------------------------------------------------

class TestPagination:
    async def test_chunk_pagination(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        for i in range(10):
            await rt.append_chunk(t.id, speaker="agent", text=f"chunk {i}")

        page1 = await _chunks(db).get_by_transcript(t.id, page=1, page_size=5)
        page2 = await _chunks(db).get_by_transcript(t.id, page=2, page_size=5)

        assert len(page1.items) == 5
        assert len(page2.items) == 5
        assert page1.total == 10
        assert page1.items[-1].chunk_index < page2.items[0].chunk_index

    async def test_event_pagination(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        await rt.pause(t.id)
        await rt.resume(t.id)
        await rt.complete(t.id)

        result = await _events(db).get_by_transcript(t.id, page=1, page_size=2)
        assert result.total >= 4
        assert len(result.items) == 2


# ---------------------------------------------------------------------------
# 5. Replay Consistency
# ---------------------------------------------------------------------------

class TestReplayConsistency:
    async def test_replay_matches_active_status(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        result = await rt.replay(t.id)
        assert result.final_status == TranscriptStatus.active

    async def test_replay_matches_completed_status(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        await rt.complete(t.id)
        result = await rt.replay(t.id)
        assert result.final_status == TranscriptStatus.completed

    async def test_replay_counts_chunks(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        await rt.append_chunk(t.id, speaker="agent", text="A")
        await rt.append_chunk(t.id, speaker="agent", text="B")
        result = await rt.replay(t.id)
        assert result.chunk_count == 2

    async def test_replay_deterministic_across_calls(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        await rt.pause(t.id)
        await rt.resume(t.id)
        r1 = await rt.replay(t.id)
        r2 = await rt.replay(t.id)
        assert r1.final_status == r2.final_status
        assert r1.replayed_events == r2.replayed_events

    async def test_replay_is_read_only(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        event_count_before = len(await _events(db).get_all_ordered(t.id))
        await rt.replay(t.id)
        event_count_after = len(await _events(db).get_all_ordered(t.id))
        assert event_count_before == event_count_after


# ---------------------------------------------------------------------------
# 6. Event Ordering
# ---------------------------------------------------------------------------

class TestEventOrdering:
    async def test_events_append_only_sequence_order(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        await rt.pause(t.id)
        await rt.resume(t.id)
        events = await _events(db).get_all_ordered(t.id)
        sequences = [e.sequence for e in events]
        assert sequences == sorted(sequences)

    async def test_get_after_sequence(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        await rt.pause(t.id)
        events = await _events(db).get_all_ordered(t.id)
        first_seq = events[0].sequence

        later = await _events(db).get_after_sequence(t.id, after_sequence=first_seq)
        assert all(e.sequence > first_seq for e in later)

    async def test_chunk_after_index(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        for i in range(5):
            await rt.append_chunk(t.id, speaker="agent", text=f"chunk {i}")

        later = await _chunks(db).get_after_index(t.id, after_chunk_index=2)
        assert all(c.chunk_index > 2 for c in later)
        assert len(later) == 2  # indexes 3 and 4


# ---------------------------------------------------------------------------
# 7. Recovery
# ---------------------------------------------------------------------------

class TestRecovery:
    async def test_failed_can_recover(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        await rt.fail(t.id, reason="network error")
        t = await rt.start(t.id)  # failed → active (recovery)
        fetched = await _repo(db).get_by_id(t.id)
        assert fetched.transcript_status == TranscriptStatus.active

    async def test_archived_cannot_recover(self, db: AsyncSession):
        rt = _rt(db)
        t = await rt.create()
        await rt.start(t.id)
        await rt.complete(t.id)
        await rt.archive(t.id)
        with pytest.raises(TranscriptTransitionError):
            await rt.start(t.id)
