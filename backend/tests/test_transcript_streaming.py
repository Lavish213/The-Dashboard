"""
Phase 9 — Transcript Runtime + Streaming Tests.

Covers:
- TranscriptSessionInput / StreamSessionInput / StreamChunkInput contracts (frozen)
- TokenUsage / StreamResult / ReconstructionResult / CheckpointResult (frozen)
- RetentionPolicy (frozen, field defaults)
- TranscriptStreamRuntime lifecycle:
    create (idempotent), start, receive_partial, commit_chunk,
    complete, interrupt, resume, cancel, fail
- State error enforcement
- TranscriptCheckpointRuntime (set, get_latest, get_all, get_for_stream, chunks_since)
- TranscriptCheckpoint idempotency (same position = same row)
- StreamReconstructor (reconstruct, reconstruct_from, reconstruct_stream)
- TranscriptTokenTracker (total_for_transcript, total_for_stream)
- TranscriptRetentionRuntime (archive, soft_delete, find_expired, find_archivable)
- TranscriptAuditLinker (link_execution, link_stream, get_linked_executions)
- TranscriptSearchIndex (build_index, search_by_source)
- Stream events appended to transcript_events
- Full streaming lifecycle integration
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import (
    TranscriptSourceType,
    TranscriptStreamStatus,
)
from transcripts.audit import TranscriptAuditLinker
from transcripts.checkpointing import TranscriptCheckpointRuntime
from transcripts.contracts import (
    CheckpointResult,
    ReconstructionResult,
    RetentionPolicy,
    StreamChunkInput,
    StreamResult,
    StreamSessionInput,
    TokenUsage,
    TranscriptSessionInput,
)
from transcripts.reconstruction import StreamReconstructor
from transcripts.repositories.event import TranscriptEventRepository
from transcripts.repositories.stream import TranscriptStreamRepository
from transcripts.retention import RetentionViolationError, TranscriptRetentionRuntime
from transcripts.runtime.runtime import TranscriptRuntime
from transcripts.search_index import TranscriptSearchIndex
from transcripts.stream import (
    EVT_STREAM_CANCELLED,
    EVT_STREAM_CHUNK_COMMITTED,
    EVT_STREAM_COMPLETED,
    EVT_STREAM_CREATED,
    EVT_STREAM_FAILED,
    EVT_STREAM_INTERRUPTED,
    EVT_STREAM_PARTIAL_UPDATED,
    EVT_STREAM_RESUMED,
    EVT_STREAM_STARTED,
    StreamStateError,
    TranscriptStreamRuntime,
)
from transcripts.token_tracker import TranscriptTokenTracker

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

async def _transcript(db: AsyncSession):
    return await TranscriptRuntime(db).create(
        source_type=TranscriptSourceType.call
    )


async def _active_transcript(db: AsyncSession):
    t = await _transcript(db)
    await TranscriptRuntime(db).start(t.id)
    return t


def _srt() -> TranscriptStreamRuntime:
    """Stream runtime factory — created inside tests with db."""
    ...  # marker; tests use TranscriptStreamRuntime(db) directly


# ---------------------------------------------------------------------------
# 1. Contracts (frozen)
# ---------------------------------------------------------------------------

class TestContracts:
    def test_session_input_frozen(self) -> None:
        inp = TranscriptSessionInput()
        with pytest.raises(Exception):
            inp.source_type = TranscriptSourceType.upload  # type: ignore[misc]

    def test_stream_session_input_frozen(self) -> None:
        inp = StreamSessionInput(transcript_id=uuid4(), stream_key="k")
        with pytest.raises(Exception):
            inp.stream_key = "x"  # type: ignore[misc]

    def test_stream_chunk_input_frozen(self) -> None:
        inp = StreamChunkInput(stream_id=uuid4(), speaker="agent", text="hi")
        with pytest.raises(Exception):
            inp.text = "mutated"  # type: ignore[misc]

    def test_token_usage_total(self) -> None:
        u = TokenUsage(tokens_input=100, tokens_output=50)
        assert u.total == 150

    def test_token_usage_frozen(self) -> None:
        u = TokenUsage(tokens_input=1, tokens_output=2)
        with pytest.raises(Exception):
            u.tokens_input = 99  # type: ignore[misc]

    def test_stream_result_frozen(self) -> None:
        r = StreamResult(
            stream_id=uuid4(),
            transcript_id=uuid4(),
            stream_key="k",
            status=TranscriptStreamStatus.pending,
            last_chunk_index=None,
            tokens_input=0,
            tokens_output=0,
        )
        with pytest.raises(Exception):
            r.status = TranscriptStreamStatus.completed  # type: ignore[misc]

    def test_retention_policy_defaults(self) -> None:
        p = RetentionPolicy()
        assert p.archive_after_days is None
        assert p.delete_after_days is None
        assert p.requires_explicit_delete is True

    def test_retention_policy_frozen(self) -> None:
        p = RetentionPolicy(archive_after_days=30)
        with pytest.raises(Exception):
            p.archive_after_days = 60  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 2. TranscriptStreamRuntime — lifecycle
# ---------------------------------------------------------------------------

class TestStreamLifecycle:
    @pytest.mark.asyncio
    async def test_create_new_stream(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        assert r.status == TranscriptStreamStatus.pending
        assert r.transcript_id == t.id

    @pytest.mark.asyncio
    async def test_create_idempotent(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        key = f"k-{uuid4()}"
        r1 = await rt.create(t.id, stream_key=key)
        r2 = await rt.create(t.id, stream_key=key)
        assert r1.stream_id == r2.stream_id

    @pytest.mark.asyncio
    async def test_create_emits_event(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        await rt.create(t.id, stream_key=f"k-{uuid4()}")
        events = await TranscriptEventRepository(db).get_all_ordered(t.id)
        types = [e.event_type for e in events]
        assert EVT_STREAM_CREATED in types

    @pytest.mark.asyncio
    async def test_start_pending_to_active(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        started = await rt.start(r.stream_id)
        assert started.status == TranscriptStreamStatus.active

    @pytest.mark.asyncio
    async def test_start_non_pending_raises(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        with pytest.raises(StreamStateError):
            await rt.start(r.stream_id)

    @pytest.mark.asyncio
    async def test_start_emits_event(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        events = await TranscriptEventRepository(db).get_all_ordered(t.id)
        types = [e.event_type for e in events]
        assert EVT_STREAM_STARTED in types

    @pytest.mark.asyncio
    async def test_receive_partial_updates_buffer(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.receive_partial(r.stream_id, "Hello wor")
        repo = TranscriptStreamRepository(db)
        row = await repo.get_by_id_or_raise(r.stream_id)
        assert row.partial_text == "Hello wor"

    @pytest.mark.asyncio
    async def test_receive_partial_emits_event(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.receive_partial(r.stream_id, "partial text")
        events = await TranscriptEventRepository(db).get_all_ordered(t.id)
        types = [e.event_type for e in events]
        assert EVT_STREAM_PARTIAL_UPDATED in types

    @pytest.mark.asyncio
    async def test_receive_partial_non_active_raises(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        # still pending
        with pytest.raises(StreamStateError):
            await rt.receive_partial(r.stream_id, "x")

    @pytest.mark.asyncio
    async def test_commit_chunk_appends_and_clears_partial(
        self, db: AsyncSession
    ) -> None:
        t = await _active_transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.receive_partial(r.stream_id, "Hello ")
        cr = await rt.commit_chunk(r.stream_id, speaker="agent", text="Hello world")
        assert cr.chunk_index == 0
        # partial cleared
        repo = TranscriptStreamRepository(db)
        row = await repo.get_by_id_or_raise(r.stream_id)
        assert row.partial_text is None
        assert row.last_chunk_index == 0

    @pytest.mark.asyncio
    async def test_commit_chunk_emits_event(self, db: AsyncSession) -> None:
        t = await _active_transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.commit_chunk(r.stream_id, speaker="agent", text="hi")
        events = await TranscriptEventRepository(db).get_all_ordered(t.id)
        types = [e.event_type for e in events]
        assert EVT_STREAM_CHUNK_COMMITTED in types

    @pytest.mark.asyncio
    async def test_commit_chunk_tracks_tokens(self, db: AsyncSession) -> None:
        t = await _active_transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.commit_chunk(r.stream_id, speaker="a", text="hi", tokens_output=10)
        cr2 = await rt.commit_chunk(r.stream_id, speaker="a", text="bye", tokens_output=5)
        assert cr2.tokens_output_cumulative == 15

    @pytest.mark.asyncio
    async def test_complete_active_stream(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        done = await rt.complete(r.stream_id, tokens_input=100, tokens_output=50)
        assert done.status == TranscriptStreamStatus.completed
        assert done.tokens_input == 100

    @pytest.mark.asyncio
    async def test_complete_clears_partial(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.receive_partial(r.stream_id, "pending text")
        await rt.complete(r.stream_id)
        repo = TranscriptStreamRepository(db)
        row = await repo.get_by_id_or_raise(r.stream_id)
        assert row.partial_text is None

    @pytest.mark.asyncio
    async def test_complete_non_active_raises(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        with pytest.raises(StreamStateError):
            await rt.complete(r.stream_id)

    @pytest.mark.asyncio
    async def test_complete_emits_event(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.complete(r.stream_id)
        events = await TranscriptEventRepository(db).get_all_ordered(t.id)
        types = [e.event_type for e in events]
        assert EVT_STREAM_COMPLETED in types

    @pytest.mark.asyncio
    async def test_interrupt_active_stream(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        interrupted = await rt.interrupt(r.stream_id, reason="network_drop")
        assert interrupted.status == TranscriptStreamStatus.interrupted

    @pytest.mark.asyncio
    async def test_interrupt_emits_event(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.interrupt(r.stream_id)
        events = await TranscriptEventRepository(db).get_all_ordered(t.id)
        types = [e.event_type for e in events]
        assert EVT_STREAM_INTERRUPTED in types

    @pytest.mark.asyncio
    async def test_resume_interrupted_stream(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.interrupt(r.stream_id)
        resumed = await rt.resume(r.stream_id)
        assert resumed.status == TranscriptStreamStatus.active

    @pytest.mark.asyncio
    async def test_resume_emits_event(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.interrupt(r.stream_id)
        await rt.resume(r.stream_id)
        events = await TranscriptEventRepository(db).get_all_ordered(t.id)
        types = [e.event_type for e in events]
        assert EVT_STREAM_RESUMED in types

    @pytest.mark.asyncio
    async def test_resume_non_interrupted_raises(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        with pytest.raises(StreamStateError):
            await rt.resume(r.stream_id)

    @pytest.mark.asyncio
    async def test_cancel_pending(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        cancelled = await rt.cancel(r.stream_id, reason="user")
        assert cancelled.status == TranscriptStreamStatus.cancelled

    @pytest.mark.asyncio
    async def test_cancel_active(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        cancelled = await rt.cancel(r.stream_id)
        assert cancelled.status == TranscriptStreamStatus.cancelled

    @pytest.mark.asyncio
    async def test_cancel_idempotent_on_completed(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.complete(r.stream_id)
        result = await rt.cancel(r.stream_id)
        assert result.status == TranscriptStreamStatus.completed

    @pytest.mark.asyncio
    async def test_cancel_emits_event(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.cancel(r.stream_id)
        events = await TranscriptEventRepository(db).get_all_ordered(t.id)
        types = [e.event_type for e in events]
        assert EVT_STREAM_CANCELLED in types

    @pytest.mark.asyncio
    async def test_fail_stream(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        failed = await rt.fail(r.stream_id, error="provider_timeout")
        assert failed.status == TranscriptStreamStatus.failed

    @pytest.mark.asyncio
    async def test_fail_emits_event(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.fail(r.stream_id, error="err")
        events = await TranscriptEventRepository(db).get_all_ordered(t.id)
        types = [e.event_type for e in events]
        assert EVT_STREAM_FAILED in types


# ---------------------------------------------------------------------------
# 3. TranscriptCheckpointRuntime
# ---------------------------------------------------------------------------

class TestCheckpointing:
    @pytest.mark.asyncio
    async def test_set_checkpoint(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        cp = await TranscriptCheckpointRuntime(db).set(
            transcript_id=t.id, chunk_index=5, label="mid"
        )
        assert isinstance(cp, CheckpointResult)
        assert cp.chunk_index == 5
        assert cp.label == "mid"

    @pytest.mark.asyncio
    async def test_checkpoint_idempotent(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        crt = TranscriptCheckpointRuntime(db)
        cp1 = await crt.set(t.id, chunk_index=3)
        cp2 = await crt.set(t.id, chunk_index=3)
        assert cp1.checkpoint_id == cp2.checkpoint_id

    @pytest.mark.asyncio
    async def test_get_latest_returns_highest_index(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        crt = TranscriptCheckpointRuntime(db)
        await crt.set(t.id, chunk_index=0)
        await crt.set(t.id, chunk_index=5)
        await crt.set(t.id, chunk_index=10)
        latest = await crt.get_latest(t.id)
        assert latest is not None
        assert latest.chunk_index == 10

    @pytest.mark.asyncio
    async def test_get_latest_none_if_no_checkpoints(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        assert await TranscriptCheckpointRuntime(db).get_latest(t.id) is None

    @pytest.mark.asyncio
    async def test_get_all_ordered(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        crt = TranscriptCheckpointRuntime(db)
        await crt.set(t.id, chunk_index=2)
        await crt.set(t.id, chunk_index=0)
        await crt.set(t.id, chunk_index=7)
        all_cps = await crt.get_all(t.id)
        indices = [c.chunk_index for c in all_cps]
        assert indices == sorted(indices)

    @pytest.mark.asyncio
    async def test_get_for_stream(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        stream_id = uuid4()
        crt = TranscriptCheckpointRuntime(db)
        await crt.set(t.id, chunk_index=1, stream_id=stream_id)
        await crt.set(t.id, chunk_index=3, stream_id=stream_id)
        # different stream
        await crt.set(t.id, chunk_index=5, stream_id=uuid4())
        cps = await crt.get_for_stream(stream_id)
        assert len(cps) == 2
        assert all(c.stream_id == stream_id for c in cps)

    @pytest.mark.asyncio
    async def test_chunks_since_returns_tail(self, db: AsyncSession) -> None:
        t = await _active_transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        # commit 3 chunks
        await rt.commit_chunk(r.stream_id, speaker="a", text="one")
        await rt.commit_chunk(r.stream_id, speaker="a", text="two")
        await rt.commit_chunk(r.stream_id, speaker="a", text="three")
        crt = TranscriptCheckpointRuntime(db)
        chunks = await crt.chunks_since(t.id, after_chunk_index=0)
        texts = [c.text for c in chunks]
        assert "two" in texts
        assert "three" in texts
        assert "one" not in texts


# ---------------------------------------------------------------------------
# 4. StreamReconstructor
# ---------------------------------------------------------------------------

class TestReconstruction:
    @pytest.mark.asyncio
    async def test_reconstruct_empty(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        result = await StreamReconstructor(db).reconstruct(t.id)
        assert result.full_text == ""
        assert result.chunk_count == 0
        assert result.speakers == []

    @pytest.mark.asyncio
    async def test_reconstruct_full(self, db: AsyncSession) -> None:
        t = await _active_transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.commit_chunk(r.stream_id, speaker="agent", text="Hello")
        await rt.commit_chunk(r.stream_id, speaker="lead", text="World")
        result = await StreamReconstructor(db).reconstruct(t.id)
        assert result.full_text == "Hello World"
        assert result.chunk_count == 2
        assert "agent" in result.speakers
        assert "lead" in result.speakers

    @pytest.mark.asyncio
    async def test_reconstruct_from_checkpoint(self, db: AsyncSession) -> None:
        t = await _active_transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.commit_chunk(r.stream_id, speaker="a", text="first")   # idx 0
        await rt.commit_chunk(r.stream_id, speaker="a", text="second")  # idx 1
        await rt.commit_chunk(r.stream_id, speaker="a", text="third")   # idx 2
        result = await StreamReconstructor(db).reconstruct_from(t.id, after_chunk_index=0)
        assert "second" in result.full_text
        assert "third" in result.full_text
        assert "first" not in result.full_text

    @pytest.mark.asyncio
    async def test_reconstruction_result_frozen(self) -> None:
        r = ReconstructionResult(
            transcript_id=uuid4(),
            full_text="x",
            chunk_count=1,
            speakers=["a"],
            from_chunk_index=0,
            to_chunk_index=0,
        )
        with pytest.raises(Exception):
            r.full_text = "mutated"  # type: ignore[misc]

    @pytest.mark.asyncio
    async def test_reconstruct_stream_no_chunks(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        result = await StreamReconstructor(db).reconstruct_stream(t.id, r.stream_id)
        assert result.chunk_count == 0
        assert result.full_text == ""


# ---------------------------------------------------------------------------
# 5. TranscriptTokenTracker
# ---------------------------------------------------------------------------

class TestTokenTracker:
    @pytest.mark.asyncio
    async def test_total_for_transcript_no_streams(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        usage = await TranscriptTokenTracker(db).total_for_transcript(t.id)
        assert usage.tokens_input == 0
        assert usage.tokens_output == 0

    @pytest.mark.asyncio
    async def test_total_for_transcript_sums_streams(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r1 = await rt.create(t.id, stream_key=f"k1-{uuid4()}")
        await rt.start(r1.stream_id)
        await rt.complete(r1.stream_id, tokens_input=100, tokens_output=50)

        r2 = await rt.create(t.id, stream_key=f"k2-{uuid4()}")
        await rt.start(r2.stream_id)
        await rt.complete(r2.stream_id, tokens_input=200, tokens_output=80)

        usage = await TranscriptTokenTracker(db).total_for_transcript(t.id)
        assert usage.tokens_input == 300
        assert usage.tokens_output == 130

    @pytest.mark.asyncio
    async def test_total_for_stream(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.complete(r.stream_id, tokens_input=77, tokens_output=33)
        usage = await TranscriptTokenTracker(db).total_for_stream(r.stream_id)
        assert usage.tokens_input == 77
        assert usage.tokens_output == 33

    @pytest.mark.asyncio
    async def test_total_for_stream_missing(self, db: AsyncSession) -> None:
        usage = await TranscriptTokenTracker(db).total_for_stream(uuid4())
        assert usage.total == 0


# ---------------------------------------------------------------------------
# 6. TranscriptRetentionRuntime
# ---------------------------------------------------------------------------

class TestRetentionRuntime:
    @pytest.mark.asyncio
    async def test_archive_transcript(self, db: AsyncSession) -> None:
        t = await _active_transcript(db)
        await TranscriptRuntime(db).complete(t.id)
        await TranscriptRetentionRuntime(db).archive(t.id)
        from models.enums import TranscriptStatus
        from transcripts.repositories.transcript import TranscriptRepository
        row = await TranscriptRepository(db).get_by_id_or_raise(t.id)
        assert row.transcript_status == TranscriptStatus.archived

    @pytest.mark.asyncio
    async def test_archive_idempotent(self, db: AsyncSession) -> None:
        t = await _active_transcript(db)
        await TranscriptRuntime(db).complete(t.id)
        rr = TranscriptRetentionRuntime(db)
        await rr.archive(t.id)
        await rr.archive(t.id)  # second call is no-op

    @pytest.mark.asyncio
    async def test_soft_delete(self, db: AsyncSession) -> None:
        from sqlalchemy import select

        from models.transcript import Transcript
        t = await _transcript(db)
        await TranscriptRetentionRuntime(db).soft_delete(
            t.id, policy=RetentionPolicy(requires_explicit_delete=False)
        )
        result = await db.execute(select(Transcript).where(Transcript.id == t.id))
        row = result.scalar_one()
        assert row.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_blocked_by_policy(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        with pytest.raises(RetentionViolationError):
            await TranscriptRetentionRuntime(db).soft_delete(
                t.id, policy=RetentionPolicy(requires_explicit_delete=True)
            )

    @pytest.mark.asyncio
    async def test_soft_delete_idempotent(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rr = TranscriptRetentionRuntime(db)
        policy = RetentionPolicy(requires_explicit_delete=False)
        await rr.soft_delete(t.id, policy=policy)
        await rr.soft_delete(t.id, policy=policy)  # no-op

    @pytest.mark.asyncio
    async def test_find_expired(self, db: AsyncSession) -> None:
        t = await _active_transcript(db)
        await TranscriptRuntime(db).complete(t.id)
        # Use a future "now" to simulate expiry
        future_now = datetime.now(UTC) + timedelta(days=400)
        expired = await TranscriptRetentionRuntime(db).find_expired(
            delete_after_days=365, now=future_now
        )
        assert t.id in expired

    @pytest.mark.asyncio
    async def test_find_archivable(self, db: AsyncSession) -> None:
        t = await _active_transcript(db)
        await TranscriptRuntime(db).complete(t.id)
        future_now = datetime.now(UTC) + timedelta(days=100)
        archivable = await TranscriptRetentionRuntime(db).find_archivable(
            archive_after_days=30, now=future_now
        )
        assert t.id in archivable


# ---------------------------------------------------------------------------
# 7. TranscriptAuditLinker
# ---------------------------------------------------------------------------

class TestAuditLinker:
    @pytest.mark.asyncio
    async def test_link_execution(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        exec_id = uuid4()
        await TranscriptAuditLinker(db).link_execution(t.id, exec_id)
        linked = await TranscriptAuditLinker(db).get_linked_executions(t.id)
        assert exec_id in linked

    @pytest.mark.asyncio
    async def test_link_multiple_executions(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        e1, e2 = uuid4(), uuid4()
        linker = TranscriptAuditLinker(db)
        await linker.link_execution(t.id, e1)
        await linker.link_execution(t.id, e2)
        linked = await linker.get_linked_executions(t.id)
        assert e1 in linked
        assert e2 in linked

    @pytest.mark.asyncio
    async def test_link_stream(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        stream_id = uuid4()
        linker = TranscriptAuditLinker(db)
        await linker.link_stream(t.id, stream_id)
        streams = await linker.get_linked_streams(t.id)
        assert stream_id in streams

    @pytest.mark.asyncio
    async def test_no_linked_executions(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        linked = await TranscriptAuditLinker(db).get_linked_executions(t.id)
        assert linked == []


# ---------------------------------------------------------------------------
# 8. TranscriptSearchIndex
# ---------------------------------------------------------------------------

class TestSearchIndex:
    @pytest.mark.asyncio
    async def test_build_index_no_chunks(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        idx = await TranscriptSearchIndex(db).build_index(t.id)
        assert idx["chunk_count"] == 0
        assert idx["speakers"] == []
        assert "indexed_at" in idx

    @pytest.mark.asyncio
    async def test_build_index_with_chunks(self, db: AsyncSession) -> None:
        t = await _active_transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.commit_chunk(r.stream_id, speaker="agent", text="hi")
        await rt.commit_chunk(r.stream_id, speaker="lead", text="bye")
        idx = await TranscriptSearchIndex(db).build_index(t.id)
        assert idx["chunk_count"] == 2
        assert set(idx["speakers"]) == {"agent", "lead"}
        assert idx["stream_count"] == 1

    @pytest.mark.asyncio
    async def test_build_index_persists_to_metadata(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        await TranscriptSearchIndex(db).build_index(t.id)
        from transcripts.repositories.transcript import TranscriptRepository
        row = await TranscriptRepository(db).get_by_id_or_raise(t.id)
        assert row.metadata_ is not None
        assert "chunk_count" in row.metadata_

    @pytest.mark.asyncio
    async def test_build_index_records_failures(self, db: AsyncSession) -> None:
        t = await _transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.fail(r.stream_id, error="timeout")
        idx = await TranscriptSearchIndex(db).build_index(t.id)
        assert idx["has_failures"] is True


# ---------------------------------------------------------------------------
# 9. Full lifecycle integration
# ---------------------------------------------------------------------------

class TestFullStreamingLifecycle:
    @pytest.mark.asyncio
    async def test_stream_with_checkpoint_and_reconstruction(
        self, db: AsyncSession
    ) -> None:
        """
        create transcript → create stream → commit chunks → checkpoint →
        interrupt → resume → commit more → complete → reconstruct full text
        """
        t = await _active_transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)

        await rt.commit_chunk(r.stream_id, speaker="agent", text="Hello")
        await rt.commit_chunk(r.stream_id, speaker="lead", text="Hi")

        # checkpoint after chunk 1
        crt = TranscriptCheckpointRuntime(db)
        cp = await crt.set(t.id, chunk_index=1, stream_id=r.stream_id, label="mid")
        assert cp.chunk_index == 1

        # interrupt + resume
        await rt.interrupt(r.stream_id, reason="network")
        await rt.resume(r.stream_id)

        await rt.commit_chunk(r.stream_id, speaker="agent", text="Goodbye")
        done = await rt.complete(r.stream_id, tokens_input=50, tokens_output=30)
        assert done.status == TranscriptStreamStatus.completed

        # full reconstruction
        rec = await StreamReconstructor(db).reconstruct(t.id)
        assert "Hello" in rec.full_text
        assert "Hi" in rec.full_text
        assert "Goodbye" in rec.full_text
        assert rec.chunk_count == 3

        # token totals
        usage = await TranscriptTokenTracker(db).total_for_transcript(t.id)
        assert usage.tokens_input == 50
        assert usage.tokens_output == 30

    @pytest.mark.asyncio
    async def test_all_stream_events_recorded(self, db: AsyncSession) -> None:
        t = await _active_transcript(db)
        rt = TranscriptStreamRuntime(db)
        r = await rt.create(t.id, stream_key=f"k-{uuid4()}")
        await rt.start(r.stream_id)
        await rt.receive_partial(r.stream_id, "part")
        await rt.commit_chunk(r.stream_id, speaker="a", text="chunk")
        await rt.complete(r.stream_id)

        events = await TranscriptEventRepository(db).get_all_ordered(t.id)
        types = {e.event_type for e in events}
        expected = {
            EVT_STREAM_CREATED, EVT_STREAM_STARTED,
            EVT_STREAM_PARTIAL_UPDATED, EVT_STREAM_CHUNK_COMMITTED,
            EVT_STREAM_COMPLETED,
        }
        assert expected <= types
