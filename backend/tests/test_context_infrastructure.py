"""
Phase 10 — Context Infrastructure tests.

Coverage:
  - ContextItem hash / equality
  - ContextWindowRuntime: no truncation, truncate_oldest, truncate_lowest_priority,
    truncate_largest, fail_on_overflow, protected layers, max_items cap
  - ContextProvenanceTracker: build, serialize, deserialize round-trip
  - ContextCacheRuntime: set/get, TTL expiry, LRU eviction, invalidate, clear
  - ContextInjectionGuardrail: budget check, layer filter, snapshot status, layer access
  - ContextRetentionRuntime: find_archivable, find_expirable, archive, expire,
    explicit-delete guard
  - ContextSnapshotRepository: create, get_by_key, get_active_for_workflow
  - ContextSnapshotRuntime: create idempotent, restore, restore_by_key
  - ContextAuditRuntime: record, get_for_snapshot
  - Adapters: transcript, workflow, ai_execution
  - ContextAssembler: full pipeline, cache hit, layer filter, truncation
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from context.assembler import ContextAssembler
from context.audit import (
    ACTION_ASSEMBLY_COMPLETED,
    ACTION_CACHE_HIT,
    ContextAuditRuntime,
)
from context.cache import ContextCacheRuntime
from context.contracts import (
    ContextAssemblyInput,
    ContextAssemblyResult,
    ContextItem,
    ContextRetentionPolicy,
    ContextWindow,
    TruncationPolicy,
)
from context.guardrails import ContextGuardrailError, ContextInjectionGuardrail
from context.provenance import ContextProvenanceTracker
from context.retention import ContextRetentionRuntime, RetentionViolationError
from context.snapshot import ContextSnapshotRuntime
from context.window import ContextWindowOverflowError, ContextWindowRuntime
from models.enums import (
    AIExecutionStatus,
    AIProviderType,
    AITaskType,
    ContextLayerType,
    ContextSnapshotStatus,
    ContextWindowStrategy,
    TranscriptSourceType,
    TranscriptStreamType,
    WorkflowStatus,
    WorkflowType,
)
from repositories.context_snapshot import ContextSnapshotRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _item(
    layer: ContextLayerType = ContextLayerType.transcript,
    token_count: int = 10,
    priority: int = 1,
    created_at: datetime | None = None,
    source_id: uuid.UUID | None = None,
) -> ContextItem:
    return ContextItem(
        layer=layer,
        source_id=source_id or uuid4(),
        source_type=layer.value,
        content="test content",
        token_count=token_count,
        priority=priority,
        created_at=created_at or datetime.now(UTC),
    )


def _assembly_input(
    key: str | None = None,
    budget: int = 100,
    layer_filter=None,
    strategy: ContextWindowStrategy = ContextWindowStrategy.truncate_oldest,
) -> ContextAssemblyInput:
    return ContextAssemblyInput(
        assembly_key=key or f"key-{uuid4()}",
        token_budget=budget,
        layer_filter=layer_filter,
        strategy=strategy,
    )


# ---------------------------------------------------------------------------
# ContextItem
# ---------------------------------------------------------------------------

class TestContextItem:
    def test_hash_equality(self):
        sid = uuid4()
        a = _item(source_id=sid, layer=ContextLayerType.transcript, priority=0)
        b = _item(source_id=sid, layer=ContextLayerType.transcript, priority=0)
        assert hash(a) == hash(b)

    def test_hash_differs_on_source(self):
        a = _item(source_id=uuid4())
        b = _item(source_id=uuid4())
        assert hash(a) != hash(b)

    def test_frozen(self):
        item = _item()
        with pytest.raises((AttributeError, TypeError)):
            item.content = "mutate"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ContextWindowRuntime
# ---------------------------------------------------------------------------

class TestContextWindowRuntime:
    def setup_method(self):
        self.rt = ContextWindowRuntime()
        self.policy = TruncationPolicy(
            strategy=ContextWindowStrategy.truncate_oldest,
            protect_layers=(ContextLayerType.system,),
        )

    def test_no_truncation_when_within_budget(self):
        items = [_item(token_count=20) for _ in range(3)]
        window = self.rt.build(items, budget=100, policy=self.policy)
        assert window.truncated is False
        assert window.total_tokens == 60
        assert len(window.items) == 3

    def test_truncate_oldest(self):
        old = _item(token_count=30, created_at=datetime(2024, 1, 1, tzinfo=UTC))
        new = _item(token_count=30, created_at=datetime(2025, 1, 1, tzinfo=UTC))
        policy = TruncationPolicy(
            strategy=ContextWindowStrategy.truncate_oldest,
            protect_layers=(),
        )
        window = self.rt.build([old, new], budget=35, policy=policy)
        assert window.truncated is True
        assert window.truncated_count == 1
        assert old not in window.items

    def test_truncate_lowest_priority(self):
        high = _item(token_count=30, priority=0)  # high importance
        low = _item(token_count=30, priority=5)   # low importance
        policy = TruncationPolicy(
            strategy=ContextWindowStrategy.truncate_lowest_priority,
            protect_layers=(),
        )
        window = self.rt.build([high, low], budget=35, policy=policy)
        assert window.truncated is True
        assert low not in window.items
        assert high in window.items

    def test_truncate_largest(self):
        big = _item(token_count=50, priority=1)
        small = _item(token_count=10, priority=1)
        policy = TruncationPolicy(
            strategy=ContextWindowStrategy.truncate_largest,
            protect_layers=(),
        )
        window = self.rt.build([big, small], budget=30, policy=policy)
        assert window.truncated is True
        assert big not in window.items
        assert small in window.items

    def test_fail_on_overflow(self):
        items = [_item(token_count=50) for _ in range(3)]
        policy = TruncationPolicy(
            strategy=ContextWindowStrategy.fail_on_overflow,
            protect_layers=(),
        )
        with pytest.raises(ContextWindowOverflowError) as exc:
            self.rt.build(items, budget=100, policy=policy)
        assert exc.value.total_tokens == 150
        assert exc.value.budget == 100

    def test_protected_layers_never_removed(self):
        sys_item = _item(layer=ContextLayerType.system, token_count=80)
        other = _item(layer=ContextLayerType.transcript, token_count=50)
        policy = TruncationPolicy(
            strategy=ContextWindowStrategy.truncate_oldest,
            protect_layers=(ContextLayerType.system,),
        )
        window = self.rt.build([sys_item, other], budget=90, policy=policy)
        assert sys_item in window.items

    def test_max_items_cap(self):
        items = [_item(token_count=5) for _ in range(10)]
        policy = TruncationPolicy(
            strategy=ContextWindowStrategy.truncate_oldest,
            protect_layers=(),
            max_items=3,
        )
        window = self.rt.build(items, budget=1000, policy=policy)
        assert len(window.items) == 3

    def test_empty_items(self):
        window = self.rt.build([], budget=100, policy=self.policy)
        assert len(window.items) == 0
        assert window.total_tokens == 0

    def test_exact_budget_fit(self):
        items = [_item(token_count=50), _item(token_count=50)]
        window = self.rt.build(items, budget=100, policy=self.policy)
        assert window.truncated is False
        assert window.total_tokens == 100


# ---------------------------------------------------------------------------
# ContextProvenanceTracker
# ---------------------------------------------------------------------------

class TestContextProvenanceTracker:
    def setup_method(self):
        self.tracker = ContextProvenanceTracker()

    def test_build_aggregates_by_source(self):
        sid = uuid4()
        items = [
            ContextItem(
                layer=ContextLayerType.transcript,
                source_id=sid,
                source_type="transcript_chunk",
                content="x",
                token_count=10,
                priority=1,
            )
            for _ in range(3)
        ]
        prov = self.tracker.build(items)
        key = f"transcript_chunk:{sid}"
        assert key in prov
        assert prov[key].item_count == 3
        assert prov[key].token_count == 30

    def test_serialize_deserialize_roundtrip(self):
        sid = uuid4()
        items = [
            ContextItem(
                layer=ContextLayerType.workflow,
                source_id=sid,
                source_type="workflow",
                content="wf content",
                token_count=20,
                priority=2,
            )
        ]
        prov = self.tracker.build(items)
        serialized = self.tracker.serialize(prov)
        restored = self.tracker.deserialize(serialized)
        key = f"workflow:{sid}"
        assert restored[key].source_id == sid
        assert restored[key].token_count == 20
        assert restored[key].layer == ContextLayerType.workflow

    def test_empty_items(self):
        prov = self.tracker.build([])
        assert prov == {}

    def test_multiple_sources(self):
        a = uuid4()
        b = uuid4()
        items = [
            ContextItem(ContextLayerType.transcript, a, "transcript_chunk", "x", 5, 1),
            ContextItem(ContextLayerType.workflow, b, "workflow", "y", 15, 2),
        ]
        prov = self.tracker.build(items)
        assert len(prov) == 2


# ---------------------------------------------------------------------------
# ContextCacheRuntime
# ---------------------------------------------------------------------------

def _fake_result(key: str) -> ContextAssemblyResult:
    return ContextAssemblyResult(
        snapshot_id=uuid4(),
        assembly_key=key,
        window=ContextWindow(
            items=(),
            total_tokens=10,
            token_budget=100,
        ),
        provenance={},
    )


class TestContextCacheRuntime:
    def setup_method(self):
        self.cache = ContextCacheRuntime(max_size=3)

    def test_set_and_get(self):
        result = _fake_result("k1")
        self.cache.set("k1", result)
        assert self.cache.get("k1") is result

    def test_miss_returns_none(self):
        assert self.cache.get("nonexistent") is None

    def test_ttl_expiry(self):
        result = _fake_result("k2")
        self.cache.set("k2", result, ttl_seconds=-1)  # already expired
        assert self.cache.get("k2") is None

    def test_lru_eviction(self):
        for i in range(4):
            self.cache.set(f"k{i}", _fake_result(f"k{i}"))
        # k0 should have been evicted (oldest)
        assert self.cache.get("k0") is None
        assert self.cache.size == 3

    def test_invalidate(self):
        self.cache.set("x", _fake_result("x"))
        self.cache.invalidate("x")
        assert self.cache.get("x") is None

    def test_clear(self):
        self.cache.set("a", _fake_result("a"))
        self.cache.set("b", _fake_result("b"))
        self.cache.clear()
        assert self.cache.size == 0

    def test_overwrite_resets_ttl(self):
        r1 = _fake_result("k")
        r2 = _fake_result("k")
        self.cache.set("k", r1)
        self.cache.set("k", r2)
        assert self.cache.get("k") is r2


# ---------------------------------------------------------------------------
# ContextInjectionGuardrail
# ---------------------------------------------------------------------------

class TestContextInjectionGuardrail:
    def setup_method(self):
        self.guard = ContextInjectionGuardrail()

    def test_valid_window_passes(self):
        window = ContextWindow(items=(), total_tokens=50, token_budget=100)
        inp = _assembly_input(budget=100)
        result = self.guard.check_window(window, inp)
        assert result.passed is True

    def test_budget_exceeded_raises(self):
        window = ContextWindow(items=(), total_tokens=150, token_budget=100)
        inp = _assembly_input(budget=100)
        with pytest.raises(ContextGuardrailError) as exc:
            self.guard.check_window(window, inp)
        assert exc.value.reason == "context_budget_exceeded"

    def test_layer_filter_violation_raises(self):
        forbidden_item = _item(layer=ContextLayerType.ai_execution)
        window = ContextWindow(
            items=(forbidden_item,),
            total_tokens=10,
            token_budget=100,
        )
        inp = _assembly_input(
            budget=100,
            layer_filter=(ContextLayerType.transcript,),
        )
        with pytest.raises(ContextGuardrailError) as exc:
            self.guard.check_window(window, inp)
        assert exc.value.reason == "context_layer_not_allowed"

    def test_snapshot_status_archived_raises(self):
        with pytest.raises(ContextGuardrailError) as exc:
            self.guard.check_snapshot_status(ContextSnapshotStatus.archived)
        assert exc.value.reason == "context_snapshot_not_injectable"

    def test_snapshot_status_expired_raises(self):
        with pytest.raises(ContextGuardrailError):
            self.guard.check_snapshot_status(ContextSnapshotStatus.expired)

    def test_snapshot_status_active_passes(self):
        result = self.guard.check_snapshot_status(ContextSnapshotStatus.active)
        assert result.passed is True

    def test_layer_access_denied_raises(self):
        with pytest.raises(ContextGuardrailError) as exc:
            self.guard.check_layer_access(
                [ContextLayerType.ai_execution],
                [ContextLayerType.transcript],
            )
        assert exc.value.reason == "context_layer_access_denied"

    def test_layer_access_allowed_passes(self):
        result = self.guard.check_layer_access(
            [ContextLayerType.transcript],
            [ContextLayerType.transcript, ContextLayerType.workflow],
        )
        assert result.passed is True


# ---------------------------------------------------------------------------
# ContextRetentionRuntime (DB tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestContextRetentionRuntime:
    async def _create_snapshot(self, db: AsyncSession, days_old: int = 0) -> object:
        repo = ContextSnapshotRepository(db)
        created_at = datetime.now(UTC) - timedelta(days=days_old)
        snap = await repo.create(
            assembly_key=f"key-{uuid4()}",
            status=ContextSnapshotStatus.active,
            token_count=10,
            token_budget=100,
            layer_types=[],
            window_payload={},
            provenance={},
            assembly_params={},
        )
        # Manually set created_at for aging tests
        snap.created_at = created_at
        db.add(snap)
        await db.flush()
        return snap

    async def test_find_archivable_returns_old_snapshots(self, db: AsyncSession):
        rt = ContextRetentionRuntime(db)
        old = await self._create_snapshot(db, days_old=10)
        await self._create_snapshot(db, days_old=1)
        policy = ContextRetentionPolicy(archive_after_days=5)
        now = datetime.now(UTC)
        results = await rt.find_archivable(policy, now=now)
        ids = [r.id for r in results]
        assert old.id in ids

    async def test_find_archivable_none_policy(self, db: AsyncSession):
        rt = ContextRetentionRuntime(db)
        policy = ContextRetentionPolicy(archive_after_days=None)
        results = await rt.find_archivable(policy)
        assert results == []

    async def test_find_expirable_raises_on_explicit_delete(self, db: AsyncSession):
        rt = ContextRetentionRuntime(db)
        policy = ContextRetentionPolicy(
            expire_after_days=1,
            requires_explicit_delete=True,
        )
        with pytest.raises(RetentionViolationError):
            await rt.find_expirable(policy)

    async def test_find_expirable_returns_old_when_allowed(self, db: AsyncSession):
        rt = ContextRetentionRuntime(db)
        old = await self._create_snapshot(db, days_old=10)
        policy = ContextRetentionPolicy(
            expire_after_days=5,
            requires_explicit_delete=False,
        )
        now = datetime.now(UTC)
        results = await rt.find_expirable(policy, now=now)
        ids = [r.id for r in results]
        assert old.id in ids

    async def test_archive_transitions_status(self, db: AsyncSession):
        rt = ContextRetentionRuntime(db)
        snap = await self._create_snapshot(db)
        archived = await rt.archive(snap)
        assert archived.status == ContextSnapshotStatus.archived

    async def test_expire_transitions_status(self, db: AsyncSession):
        rt = ContextRetentionRuntime(db)
        snap = await self._create_snapshot(db)
        policy = ContextRetentionPolicy(requires_explicit_delete=False)
        expired = await rt.expire(snap, policy=policy)
        assert expired.status == ContextSnapshotStatus.expired

    async def test_expire_blocks_when_requires_explicit_delete(self, db: AsyncSession):
        rt = ContextRetentionRuntime(db)
        snap = await self._create_snapshot(db)
        policy = ContextRetentionPolicy(requires_explicit_delete=True)
        with pytest.raises(RetentionViolationError):
            await rt.expire(snap, policy=policy)

    async def test_find_expirable_none_policy(self, db: AsyncSession):
        rt = ContextRetentionRuntime(db)
        policy = ContextRetentionPolicy(expire_after_days=None, requires_explicit_delete=False)
        results = await rt.find_expirable(policy)
        assert results == []


# ---------------------------------------------------------------------------
# ContextSnapshotRepository (DB tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestContextSnapshotRepository:
    async def test_create_and_get_by_id(self, db: AsyncSession):
        repo = ContextSnapshotRepository(db)
        key = f"snap-{uuid4()}"
        snap = await repo.create(
            assembly_key=key,
            status=ContextSnapshotStatus.active,
            token_count=50,
            token_budget=100,
            layer_types=["transcript"],
            window_payload={"items": []},
            provenance={},
            assembly_params={"strategy": "truncate_oldest"},
        )
        assert snap.id is not None
        fetched = await repo.get_by_id(snap.id)
        assert fetched is not None
        assert fetched.assembly_key == key

    async def test_get_by_key_returns_existing(self, db: AsyncSession):
        repo = ContextSnapshotRepository(db)
        key = f"snap-{uuid4()}"
        snap = await repo.create(
            assembly_key=key,
            status=ContextSnapshotStatus.active,
            token_count=10,
            token_budget=100,
            layer_types=[],
            window_payload={},
            provenance={},
            assembly_params={},
        )
        found = await repo.get_by_key(key)
        assert found is not None
        assert found.id == snap.id

    async def test_get_by_key_missing_returns_none(self, db: AsyncSession):
        repo = ContextSnapshotRepository(db)
        result = await repo.get_by_key("nonexistent-key")
        assert result is None

    async def test_get_active_for_workflow(self, db: AsyncSession):
        repo = ContextSnapshotRepository(db)
        wf_id = uuid4()
        snap = await repo.create(
            assembly_key=f"snap-{uuid4()}",
            status=ContextSnapshotStatus.active,
            workflow_id=wf_id,
            token_count=10,
            token_budget=100,
            layer_types=[],
            window_payload={},
            provenance={},
            assembly_params={},
        )
        results = await repo.get_active_for_workflow(wf_id)
        assert any(r.id == snap.id for r in results)

    async def test_get_active_excludes_archived(self, db: AsyncSession):
        repo = ContextSnapshotRepository(db)
        wf_id = uuid4()
        snap = await repo.create(
            assembly_key=f"snap-{uuid4()}",
            status=ContextSnapshotStatus.archived,
            workflow_id=wf_id,
            token_count=10,
            token_budget=100,
            layer_types=[],
            window_payload={},
            provenance={},
            assembly_params={},
        )
        results = await repo.get_active_for_workflow(wf_id)
        assert all(r.id != snap.id for r in results)


# ---------------------------------------------------------------------------
# ContextSnapshotRuntime (DB tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestContextSnapshotRuntime:
    def _make_window(self, tokens: int = 30) -> ContextWindow:
        item = _item(token_count=tokens)
        return ContextWindow(
            items=(item,),
            total_tokens=tokens,
            token_budget=100,
        )

    async def test_create_persists_snapshot(self, db: AsyncSession):
        rt = ContextSnapshotRuntime(db)
        inp = _assembly_input()
        window = self._make_window()
        result = await rt.create(inp, window, {})
        assert result.snapshot_id is not None
        assert result.assembly_key == inp.assembly_key
        assert result.from_cache is False

    async def test_create_idempotent_same_key(self, db: AsyncSession):
        rt = ContextSnapshotRuntime(db)
        inp = _assembly_input(key="idempotent-key")
        window = self._make_window()
        r1 = await rt.create(inp, window, {})
        r2 = await rt.create(inp, window, {})
        assert r1.snapshot_id == r2.snapshot_id
        assert r2.from_cache is True

    async def test_restore_by_id(self, db: AsyncSession):
        rt = ContextSnapshotRuntime(db)
        inp = _assembly_input()
        window = self._make_window()
        created = await rt.create(inp, window, {"key": "val"})
        restored = await rt.restore(created.snapshot_id)
        assert restored is not None
        assert restored.snapshot_id == created.snapshot_id
        assert len(restored.window.items) == 1

    async def test_restore_by_key(self, db: AsyncSession):
        rt = ContextSnapshotRuntime(db)
        inp = _assembly_input(key="restore-by-key-test")
        window = self._make_window()
        await rt.create(inp, window, {})
        restored = await rt.restore_by_key("restore-by-key-test")
        assert restored is not None
        assert restored.assembly_key == "restore-by-key-test"

    async def test_restore_missing_returns_none(self, db: AsyncSession):
        rt = ContextSnapshotRuntime(db)
        result = await rt.restore(uuid4())
        assert result is None

    async def test_restore_preserves_token_count(self, db: AsyncSession):
        rt = ContextSnapshotRuntime(db)
        inp = _assembly_input()
        window = self._make_window(tokens=42)
        await rt.create(inp, window, {})
        restored = await rt.restore_by_key(inp.assembly_key)
        assert restored is not None
        assert restored.window.total_tokens == 42


# ---------------------------------------------------------------------------
# ContextAuditRuntime (DB tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestContextAuditRuntime:
    async def test_record_and_retrieve(self, db: AsyncSession):
        rt = ContextAuditRuntime(db)
        snap_id = uuid4()
        entry = await rt.record(
            action=ACTION_ASSEMBLY_COMPLETED,
            snapshot_id=snap_id,
            payload={"token_count": 50},
        )
        assert entry.entry_id is not None
        assert entry.action == ACTION_ASSEMBLY_COMPLETED
        assert entry.snapshot_id == snap_id

    async def test_get_for_snapshot_ordered(self, db: AsyncSession):
        rt = ContextAuditRuntime(db)
        snap_id = uuid4()
        await rt.record(action="ctx_event_1", snapshot_id=snap_id)
        await rt.record(action="ctx_event_2", snapshot_id=snap_id)
        entries = await rt.get_for_snapshot(snap_id)
        actions = [e.action for e in entries]
        assert "ctx_event_1" in actions
        assert "ctx_event_2" in actions

    async def test_record_no_snapshot_id(self, db: AsyncSession):
        rt = ContextAuditRuntime(db)
        entry = await rt.record(action="context_guardrail_violation", payload={"reason": "test"})
        assert entry.snapshot_id is None

    async def test_get_for_snapshot_empty(self, db: AsyncSession):
        rt = ContextAuditRuntime(db)
        entries = await rt.get_for_snapshot(uuid4())
        assert entries == []


# ---------------------------------------------------------------------------
# Adapters (DB tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestTranscriptContextAdapter:
    async def _create_transcript(self, db: AsyncSession) -> object:
        from models.transcript import Transcript
        t = Transcript(
            source_type=TranscriptSourceType.call,
        )
        db.add(t)
        await db.flush()
        return t

    async def _create_chunk(self, db: AsyncSession, transcript_id, chunk_index: int):
        from models.transcript_chunk import TranscriptChunk
        chunk = TranscriptChunk(
            transcript_id=transcript_id,
            chunk_index=chunk_index,
            speaker="agent",
            text="hello world",
            stream_type=TranscriptStreamType.agent,
        )
        db.add(chunk)
        await db.flush()
        return chunk

    async def test_load_returns_context_items(self, db: AsyncSession):
        from context.adapters.transcript import TranscriptContextAdapter
        t = await self._create_transcript(db)
        await self._create_chunk(db, t.id, 0)
        await self._create_chunk(db, t.id, 1)
        adapter = TranscriptContextAdapter(db)
        items = await adapter.load(t.id)
        assert len(items) == 2
        assert all(i.layer == ContextLayerType.transcript for i in items)

    async def test_load_range_filter(self, db: AsyncSession):
        from context.adapters.transcript import TranscriptContextAdapter
        t = await self._create_transcript(db)
        for i in range(5):
            await self._create_chunk(db, t.id, i)
        adapter = TranscriptContextAdapter(db)
        items = await adapter.load(t.id, from_chunk_index=2, to_chunk_index=3)
        assert len(items) == 2

    async def test_load_empty_transcript(self, db: AsyncSession):
        from context.adapters.transcript import TranscriptContextAdapter
        t = await self._create_transcript(db)
        adapter = TranscriptContextAdapter(db)
        items = await adapter.load(t.id)
        assert items == []


@pytest.mark.asyncio
class TestWorkflowContextAdapter:
    async def _create_workflow(self, db: AsyncSession) -> object:
        from models.workflow import Workflow
        wf = Workflow(
            workflow_type=WorkflowType.outreach,
            workflow_status=WorkflowStatus.active,
            current_step="step_1",
        )
        db.add(wf)
        await db.flush()
        return wf

    async def test_load_returns_context_item(self, db: AsyncSession):
        from context.adapters.workflow import WorkflowContextAdapter
        wf = await self._create_workflow(db)
        adapter = WorkflowContextAdapter(db)
        items = await adapter.load(wf.id)
        assert len(items) == 1
        assert items[0].layer == ContextLayerType.workflow
        assert "outreach" in items[0].content

    async def test_load_missing_workflow_returns_empty(self, db: AsyncSession):
        from context.adapters.workflow import WorkflowContextAdapter
        adapter = WorkflowContextAdapter(db)
        items = await adapter.load(uuid4())
        assert items == []


@pytest.mark.asyncio
class TestAIExecutionContextAdapter:
    async def _create_execution(self, db: AsyncSession) -> object:
        from models.ai_execution import AIExecution
        exe = AIExecution(
            execution_key=f"key-{uuid4()}",
            task_type=AITaskType.inference,
            provider=AIProviderType.noop,
            model_name="noop",
            status=AIExecutionStatus.completed,
            input_payload={"prompt": "test"},
            output_payload={"answer": "42"},
            token_budget=100,
        )
        db.add(exe)
        await db.flush()
        return exe

    async def test_load_returns_context_item(self, db: AsyncSession):
        from context.adapters.ai_execution import AIExecutionContextAdapter
        exe = await self._create_execution(db)
        adapter = AIExecutionContextAdapter(db)
        items = await adapter.load(exe.id)
        assert len(items) == 1
        assert items[0].layer == ContextLayerType.ai_execution
        assert "inference" in items[0].content

    async def test_load_missing_execution_returns_empty(self, db: AsyncSession):
        from context.adapters.ai_execution import AIExecutionContextAdapter
        adapter = AIExecutionContextAdapter(db)
        items = await adapter.load(uuid4())
        assert items == []


# ---------------------------------------------------------------------------
# ContextAssembler (full pipeline, DB tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestContextAssembler:
    async def test_assemble_persists_snapshot_and_returns_result(self, db: AsyncSession):
        cache = ContextCacheRuntime()
        assembler = ContextAssembler(db, cache=cache)
        inp = _assembly_input(budget=200)
        items = [_item(token_count=20) for _ in range(4)]
        result = await assembler.assemble(inp, items)
        assert result.snapshot_id is not None
        assert result.from_cache is False
        assert result.window.total_tokens == 80

    async def test_assemble_cache_hit_skips_db_write(self, db: AsyncSession):
        cache = ContextCacheRuntime()
        assembler = ContextAssembler(db, cache=cache)
        inp = _assembly_input(key="cache-test")
        items = [_item(token_count=10)]
        r1 = await assembler.assemble(inp, items)
        r2 = await assembler.assemble(inp, items)
        assert r2.from_cache is True
        assert r1.snapshot_id == r2.snapshot_id

    async def test_assemble_applies_layer_filter(self, db: AsyncSession):
        cache = ContextCacheRuntime()
        assembler = ContextAssembler(db, cache=cache)
        inp = _assembly_input(
            budget=200,
            layer_filter=(ContextLayerType.transcript,),
        )
        items = [
            _item(layer=ContextLayerType.transcript, token_count=10),
            _item(layer=ContextLayerType.workflow, token_count=10),
            _item(layer=ContextLayerType.ai_execution, token_count=10),
        ]
        result = await assembler.assemble(inp, items)
        # Only transcript items in window
        assert all(i.layer == ContextLayerType.transcript for i in result.window.items)
        assert result.window.total_tokens == 10

    async def test_assemble_truncates_when_over_budget(self, db: AsyncSession):
        cache = ContextCacheRuntime()
        assembler = ContextAssembler(db, cache=cache)
        inp = _assembly_input(budget=25)
        items = [_item(token_count=10) for _ in range(5)]  # 50 total
        result = await assembler.assemble(inp, items)
        assert result.window.truncated is True
        assert result.window.total_tokens <= 25

    async def test_assemble_records_audit_entry(self, db: AsyncSession):
        cache = ContextCacheRuntime()
        assembler = ContextAssembler(db, cache=cache)
        inp = _assembly_input(key="audit-test")
        items = [_item(token_count=5)]
        result = await assembler.assemble(inp, items)
        audit_rt = ContextAuditRuntime(db)
        entries = await audit_rt.get_for_snapshot(result.snapshot_id)
        actions = [e.action for e in entries]
        assert ACTION_ASSEMBLY_COMPLETED in actions

    async def test_assemble_records_cache_hit_audit(self, db: AsyncSession):
        cache = ContextCacheRuntime()
        assembler = ContextAssembler(db, cache=cache)
        inp = _assembly_input(key="cache-audit-test")
        items = [_item(token_count=5)]
        await assembler.assemble(inp, items)
        # Second call — cache hit
        await assembler.assemble(inp, items)
        # Cache hit audit has no snapshot_id target
        from sqlalchemy import select

        from models.audit_log import AuditLog
        result = await db.execute(
            select(AuditLog).where(AuditLog.action == ACTION_CACHE_HIT)
        )
        entries = result.scalars().all()
        assert len(entries) >= 1

    async def test_assemble_provenance_populated(self, db: AsyncSession):
        cache = ContextCacheRuntime()
        assembler = ContextAssembler(db, cache=cache)
        inp = _assembly_input(key="prov-test")
        sid = uuid4()
        items = [
            ContextItem(
                layer=ContextLayerType.transcript,
                source_id=sid,
                source_type="transcript_chunk",
                content="text",
                token_count=10,
                priority=1,
            )
        ]
        result = await assembler.assemble(inp, items)
        assert result.provenance != {}
        key = f"transcript_chunk:{sid}"
        assert key in result.provenance

    async def test_assemble_empty_items(self, db: AsyncSession):
        cache = ContextCacheRuntime()
        assembler = ContextAssembler(db, cache=cache)
        inp = _assembly_input()
        result = await assembler.assemble(inp, [])
        assert result.window.total_tokens == 0
        assert len(result.window.items) == 0
