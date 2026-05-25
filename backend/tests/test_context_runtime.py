"""
Phase 15 — Context Runtime tests.

Coverage:
  - ContextBudgetLevel enum values
  - ContextError hierarchy: ContextBudgetExceededError, ContextSanitizationError,
    ContextReplayError, ContextMemoryError
  - ContextBudgetEnforcer: enforce, enforce_all, within_budget
  - ContextItemRanker: rank_by_priority, rank_by_recency, rank_by_score, top_n
  - ContextItemSanitizer: clean pass, empty content, oversized, secret patterns, batch
  - ContextMemoryRuntime: register, load, clear, budget overflow, forbidden scope,
    active_scopes, scope isolation
  - ContextReplayRuntime: reconstruct, reconstruct_by_key, expired blocked, archived blocked,
    not found raises
  - ContextRuntime: lazy init, assemble, reconstruct, check_budget, stateless properties
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from context.budget import ContextBudgetEnforcer
from context.contracts import (
    ContextAssemblyInput,
    ContextItem,
)
from context.exceptions import (
    ContextBudgetExceededError,
    ContextError,
    ContextMemoryError,
    ContextReplayError,
    ContextSanitizationError,
)
from context.memory import ContextMemoryRuntime
from context.ranking import ContextItemRanker
from context.replay import ContextReplayRuntime
from context.runtime import ContextRuntime
from context.sanitizer import ContextItemSanitizer
from models.enums import (
    ContextBudgetLevel,
    ContextLayerType,
    ContextWindowStrategy,
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
    content: str = "test content",
) -> ContextItem:
    return ContextItem(
        layer=layer,
        source_id=source_id or uuid4(),
        source_type=layer.value,
        content=content,
        token_count=token_count,
        priority=priority,
        created_at=created_at or datetime.now(UTC),
    )


def _assembly_input(
    key: str | None = None,
    budget: int = 200,
    strategy: ContextWindowStrategy = ContextWindowStrategy.truncate_oldest,
) -> ContextAssemblyInput:
    return ContextAssemblyInput(
        assembly_key=key or f"key-{uuid4()}",
        token_budget=budget,
        strategy=strategy,
    )


# ---------------------------------------------------------------------------
# ContextBudgetLevel enum
# ---------------------------------------------------------------------------


class TestContextBudgetLevelEnum:
    def test_all_five_levels_exist(self):
        levels = {lvl.value for lvl in ContextBudgetLevel}
        assert levels == {"platform", "phase", "graph", "agent", "call"}

    def test_str_enum(self):
        assert str(ContextBudgetLevel.platform) == "platform"
        assert str(ContextBudgetLevel.call) == "call"


# ---------------------------------------------------------------------------
# ContextError hierarchy
# ---------------------------------------------------------------------------


class TestContextExceptions:
    def test_budget_exceeded_error_is_context_error(self):
        err = ContextBudgetExceededError(
            level="agent", budget=100, actual=150, scope="wf-1"
        )
        assert isinstance(err, ContextError)
        assert err.level == "agent"
        assert err.budget == 100
        assert err.actual == 150
        assert err.scope == "wf-1"
        assert "150" in str(err)
        assert "100" in str(err)

    def test_sanitization_error_is_context_error(self):
        err = ContextSanitizationError(reason="secret found", field="content")
        assert isinstance(err, ContextError)
        assert err.reason == "secret found"
        assert err.field == "content"
        assert "content" in str(err)

    def test_replay_error_is_context_error(self):
        sid = uuid4()
        err = ContextReplayError(snapshot_id=sid, reason="expired")
        assert isinstance(err, ContextError)
        assert err.snapshot_id == sid
        assert err.reason == "expired"
        assert "expired" in str(err)

    def test_memory_error_is_context_error(self):
        err = ContextMemoryError(scope="session:abc", reason="budget exceeded")
        assert isinstance(err, ContextError)
        assert err.scope == "session:abc"
        assert "session:abc" in str(err)

    def test_sanitization_error_no_field(self):
        err = ContextSanitizationError(reason="bad content")
        assert err.field is None
        assert "bad content" in str(err)


# ---------------------------------------------------------------------------
# ContextBudgetEnforcer
# ---------------------------------------------------------------------------


class TestContextBudgetEnforcer:
    def setup_method(self):
        self.enforcer = ContextBudgetEnforcer()

    def test_within_budget_passes(self):
        self.enforcer.enforce(ContextBudgetLevel.agent, actual=50, budget=100)

    def test_at_budget_limit_passes(self):
        self.enforcer.enforce(ContextBudgetLevel.agent, actual=100, budget=100)

    def test_over_budget_raises(self):
        with pytest.raises(ContextBudgetExceededError) as exc_info:
            self.enforcer.enforce(ContextBudgetLevel.agent, actual=101, budget=100)
        err = exc_info.value
        assert err.level == "agent"
        assert err.budget == 100
        assert err.actual == 101

    def test_zero_budget_raises(self):
        with pytest.raises(ContextBudgetExceededError):
            self.enforcer.enforce(ContextBudgetLevel.call, actual=0, budget=0)

    def test_negative_budget_raises(self):
        with pytest.raises(ContextBudgetExceededError):
            self.enforcer.enforce(ContextBudgetLevel.call, actual=1, budget=-1)

    def test_scope_propagated(self):
        with pytest.raises(ContextBudgetExceededError) as exc_info:
            self.enforcer.enforce(
                ContextBudgetLevel.graph, actual=200, budget=100, scope="wf-abc"
            )
        assert exc_info.value.scope == "wf-abc"

    def test_enforce_all_passes_when_all_within(self):
        usage = {
            ContextBudgetLevel.platform: 1000,
            ContextBudgetLevel.agent: 500,
        }
        budgets = {
            ContextBudgetLevel.platform: 2000,
            ContextBudgetLevel.agent: 800,
        }
        self.enforcer.enforce_all(usage, budgets)

    def test_enforce_all_raises_on_first_violation(self):
        usage = {
            ContextBudgetLevel.platform: 3000,  # over
            ContextBudgetLevel.agent: 500,
        }
        budgets = {
            ContextBudgetLevel.platform: 2000,
            ContextBudgetLevel.agent: 800,
        }
        with pytest.raises(ContextBudgetExceededError) as exc_info:
            self.enforcer.enforce_all(usage, budgets)
        assert exc_info.value.level == "platform"

    def test_within_budget_true(self):
        assert self.enforcer.within_budget(ContextBudgetLevel.call, actual=50, budget=100)

    def test_within_budget_false_over(self):
        assert not self.enforcer.within_budget(ContextBudgetLevel.call, actual=101, budget=100)

    def test_within_budget_false_zero_budget(self):
        assert not self.enforcer.within_budget(ContextBudgetLevel.call, actual=0, budget=0)


# ---------------------------------------------------------------------------
# ContextItemRanker
# ---------------------------------------------------------------------------


class TestContextItemRanker:
    def setup_method(self):
        self.ranker = ContextItemRanker()

    def test_rank_by_priority_lowest_number_first(self):
        a = _item(priority=3)
        b = _item(priority=1)
        c = _item(priority=5)
        ranked = self.ranker.rank_by_priority([a, b, c])
        assert ranked[0].priority == 1
        assert ranked[1].priority == 3
        assert ranked[2].priority == 5

    def test_rank_by_priority_tie_broken_by_age(self):
        old = _item(priority=1, created_at=datetime(2024, 1, 1, tzinfo=UTC))
        new = _item(priority=1, created_at=datetime(2025, 1, 1, tzinfo=UTC))
        ranked = self.ranker.rank_by_priority([new, old])
        assert ranked[0] is old  # older first on tie

    def test_rank_by_recency_newest_first(self):
        old = _item(created_at=datetime(2024, 1, 1, tzinfo=UTC))
        new = _item(created_at=datetime(2025, 1, 1, tzinfo=UTC))
        ranked = self.ranker.rank_by_recency([old, new])
        assert ranked[0] is new

    def test_rank_by_score_highest_first(self):
        a = _item(source_id=(sid_a := uuid4()))
        b = _item(source_id=(sid_b := uuid4()))
        c = _item(source_id=(sid_c := uuid4()))
        scores = {sid_a: 0.5, sid_b: 0.9, sid_c: 0.1}
        ranked = self.ranker.rank_by_score([a, b, c], scores)
        assert ranked[0].source_id == sid_b
        assert ranked[-1].source_id == sid_c

    def test_rank_by_score_missing_score_defaults_to_zero(self):
        a = _item(source_id=(sid_a := uuid4()))
        b = _item(source_id=uuid4())  # no score entry
        scores = {sid_a: 1.0}
        ranked = self.ranker.rank_by_score([a, b], scores)
        assert ranked[0].source_id == sid_a

    def test_top_n_priority(self):
        items = [_item(priority=i) for i in range(5)]
        top = self.ranker.top_n(items, 2, strategy="priority")
        assert len(top) == 2
        assert all(i.priority < 2 for i in top)

    def test_top_n_recency(self):
        items = [
            _item(created_at=datetime(2024, i + 1, 1, tzinfo=UTC))
            for i in range(5)
        ]
        top = self.ranker.top_n(items, 2, strategy="recency")
        assert len(top) == 2

    def test_top_n_returns_all_if_n_larger(self):
        items = [_item() for _ in range(3)]
        top = self.ranker.top_n(items, 10)
        assert len(top) == 3

    def test_deterministic_same_input_same_output(self):
        items = [_item(priority=i % 3) for i in range(6)]
        r1 = self.ranker.rank_by_priority(items)
        r2 = self.ranker.rank_by_priority(items)
        assert [i.source_id for i in r1] == [i.source_id for i in r2]


# ---------------------------------------------------------------------------
# ContextItemSanitizer
# ---------------------------------------------------------------------------


class TestContextItemSanitizer:
    def setup_method(self):
        self.sanitizer = ContextItemSanitizer()

    def test_clean_item_passes(self):
        item = _item(content="This is normal conversation content.")
        result = self.sanitizer.sanitize(item)
        assert result is item

    def test_empty_content_raises(self):
        item = _item(content="")
        with pytest.raises(ContextSanitizationError) as exc_info:
            self.sanitizer.sanitize(item)
        assert exc_info.value.field == "content"

    def test_whitespace_only_raises(self):
        item = _item(content="   \t\n  ")
        with pytest.raises(ContextSanitizationError):
            self.sanitizer.sanitize(item)

    def test_oversized_content_raises(self):
        sanitizer = ContextItemSanitizer(max_content_chars=10)
        item = _item(content="x" * 11)
        with pytest.raises(ContextSanitizationError) as exc_info:
            sanitizer.sanitize(item)
        assert "too large" in exc_info.value.reason

    def test_api_key_pattern_raises(self):
        item = _item(content="Connecting with api_key: sk-abcdefghijklmnop")
        with pytest.raises(ContextSanitizationError) as exc_info:
            self.sanitizer.sanitize(item)
        assert "api_key" in exc_info.value.reason

    def test_bearer_token_raises(self):
        item = _item(content="Authorization: Bearer eyJhbGciOiJSUzI1NiJ9.payload.sig")
        with pytest.raises(ContextSanitizationError) as exc_info:
            self.sanitizer.sanitize(item)
        assert "bearer_token" in exc_info.value.reason

    def test_private_key_raises(self):
        item = _item(content="-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAK")
        with pytest.raises(ContextSanitizationError) as exc_info:
            self.sanitizer.sanitize(item)
        assert "private_key" in exc_info.value.reason

    def test_aws_key_raises(self):
        # Real AWS access key format: AKIA + exactly 16 uppercase alphanumeric chars
        item = _item(content="AWS key: AKIAIOSFODNN7EXAMPLE here")
        with pytest.raises(ContextSanitizationError) as exc_info:
            self.sanitizer.sanitize(item)
        assert "aws_key" in exc_info.value.reason

    def test_password_field_raises(self):
        item = _item(content="password: supersecretpassword123")
        with pytest.raises(ContextSanitizationError) as exc_info:
            self.sanitizer.sanitize(item)
        assert "password_field" in exc_info.value.reason

    def test_is_clean_true_for_safe_item(self):
        item = _item(content="safe text here")
        assert self.sanitizer.is_clean(item)

    def test_is_clean_false_for_secret(self):
        item = _item(content="api_key: abcdefghijklmnop")
        assert not self.sanitizer.is_clean(item)

    def test_sanitize_batch_all_clean_passes(self):
        items = [_item(content=f"content {i}") for i in range(3)]
        result = self.sanitizer.sanitize_batch(items)
        assert len(result) == 3

    def test_sanitize_batch_raises_on_any_violation(self):
        items = [
            _item(content="clean"),
            _item(content="api_key: secretsecretsecret"),
            _item(content="also clean"),
        ]
        with pytest.raises(ContextSanitizationError):
            self.sanitizer.sanitize_batch(items)


# ---------------------------------------------------------------------------
# ContextMemoryRuntime
# ---------------------------------------------------------------------------


class TestContextMemoryRuntime:
    def setup_method(self):
        self.memory = ContextMemoryRuntime()

    def test_register_and_load(self):
        item = _item(token_count=50)
        self.memory.register("session:abc", item, budget=200)
        loaded = self.memory.load("session:abc")
        assert len(loaded) == 1
        assert loaded[0] is item

    def test_load_unknown_scope_returns_empty(self):
        result = self.memory.load("session:unknown")
        assert result == []

    def test_budget_overflow_raises(self):
        item1 = _item(token_count=150)
        item2 = _item(token_count=100)
        self.memory.register("session:x", item1, budget=200)
        with pytest.raises(ContextMemoryError) as exc_info:
            self.memory.register("session:x", item2)
        assert "budget exceeded" in exc_info.value.reason

    def test_global_scope_forbidden(self):
        item = _item()
        with pytest.raises(ContextMemoryError) as exc_info:
            self.memory.register("global", item)
        assert exc_info.value.scope == "global"
        assert "forbidden" in exc_info.value.reason

    def test_global_scope_load_forbidden(self):
        with pytest.raises(ContextMemoryError):
            self.memory.load("global")

    def test_empty_scope_forbidden(self):
        item = _item()
        with pytest.raises(ContextMemoryError):
            self.memory.register("", item)

    def test_clear_scope(self):
        item = _item(token_count=50)
        self.memory.register("scope:1", item, budget=200)
        self.memory.clear("scope:1")
        assert self.memory.load("scope:1") == []
        assert not self.memory.scope_exists("scope:1")

    def test_scope_isolation(self):
        a = _item(token_count=10)
        b = _item(token_count=10)
        self.memory.register("scope:a", a, budget=100)
        self.memory.register("scope:b", b, budget=100)
        assert self.memory.load("scope:a") == [a]
        assert self.memory.load("scope:b") == [b]

    def test_total_tokens(self):
        self.memory.register("scope:t", _item(token_count=30), budget=200)
        self.memory.register("scope:t", _item(token_count=40))
        assert self.memory.total_tokens("scope:t") == 70

    def test_active_scopes(self):
        self.memory.register("scope:p", _item(token_count=10), budget=100)
        self.memory.register("scope:q", _item(token_count=10), budget=100)
        assert set(self.memory.active_scopes) == {"scope:p", "scope:q"}

    def test_budget_set_only_on_first_register(self):
        # Budget from first call wins; subsequent calls reuse the stored budget
        self.memory.register("scope:z", _item(token_count=30), budget=50)
        # Second call with a different budget — original 50 should still apply
        self.memory.register("scope:z", _item(token_count=10), budget=9999)
        assert self.memory.total_tokens("scope:z") == 40


# ---------------------------------------------------------------------------
# ContextReplayRuntime
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestContextReplayRuntime:
    async def test_reconstruct_active_snapshot(self, db: AsyncSession):
        from context.assembler import ContextAssembler

        # Create a snapshot via the assembler
        assembler = ContextAssembler(db)
        items = [_item(token_count=10) for _ in range(3)]
        inp = _assembly_input(budget=100)
        result = await assembler.assemble(inp, items)

        replay = ContextReplayRuntime(db)
        reconstructed = await replay.reconstruct(result.snapshot_id)
        assert reconstructed.snapshot_id == result.snapshot_id
        assert reconstructed.assembly_key == inp.assembly_key

    async def test_reconstruct_by_key_active_snapshot(self, db: AsyncSession):
        from context.assembler import ContextAssembler

        assembler = ContextAssembler(db)
        items = [_item(token_count=10)]
        inp = _assembly_input(budget=100)
        await assembler.assemble(inp, items)

        replay = ContextReplayRuntime(db)
        reconstructed = await replay.reconstruct_by_key(inp.assembly_key)
        assert reconstructed.assembly_key == inp.assembly_key

    async def test_reconstruct_not_found_raises(self, db: AsyncSession):
        replay = ContextReplayRuntime(db)
        with pytest.raises(ContextReplayError) as exc_info:
            await replay.reconstruct(uuid4())
        assert "not found" in exc_info.value.reason

    async def test_reconstruct_by_key_not_found_raises(self, db: AsyncSession):
        replay = ContextReplayRuntime(db)
        with pytest.raises(ContextReplayError) as exc_info:
            await replay.reconstruct_by_key("nonexistent-key-xyz")
        assert "not found" in exc_info.value.reason

    async def test_reconstruct_expired_snapshot_blocked(self, db: AsyncSession):
        from context.assembler import ContextAssembler
        from context.retention import ContextRetentionRuntime

        assembler = ContextAssembler(db)
        items = [_item(token_count=5)]
        inp = _assembly_input(budget=100)
        result = await assembler.assemble(inp, items)

        # Expire the snapshot
        repo = ContextSnapshotRepository(db)
        snapshot = await repo.get_by_id(result.snapshot_id)
        retention = ContextRetentionRuntime(db)
        await retention.expire(snapshot, policy=None)

        replay = ContextReplayRuntime(db)
        with pytest.raises(ContextReplayError) as exc_info:
            await replay.reconstruct(result.snapshot_id)
        assert "expired" in exc_info.value.reason

    async def test_reconstruct_archived_snapshot_blocked(self, db: AsyncSession):
        from context.assembler import ContextAssembler
        from context.retention import ContextRetentionRuntime

        assembler = ContextAssembler(db)
        items = [_item(token_count=5)]
        inp = _assembly_input(budget=100)
        result = await assembler.assemble(inp, items)

        repo = ContextSnapshotRepository(db)
        snapshot = await repo.get_by_id(result.snapshot_id)
        retention = ContextRetentionRuntime(db)
        await retention.archive(snapshot)

        replay = ContextReplayRuntime(db)
        with pytest.raises(ContextReplayError) as exc_info:
            await replay.reconstruct(result.snapshot_id)
        assert "archived" in exc_info.value.reason


# ---------------------------------------------------------------------------
# ContextRuntime
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestContextRuntime:
    async def test_lazy_init_does_not_construct_all(self, db: AsyncSession):
        runtime = ContextRuntime(db)
        # Before accessing lazy props, internal handles should be None
        assert runtime._assembler is None
        assert runtime._replay is None
        assert runtime._audit is None

    async def test_assembler_property_lazy_init(self, db: AsyncSession):
        runtime = ContextRuntime(db)
        from context.assembler import ContextAssembler
        assembler = runtime.assembler
        assert isinstance(assembler, ContextAssembler)
        # Second access returns same instance
        assert runtime.assembler is assembler

    async def test_stateless_primitives_always_available(self, db: AsyncSession):
        runtime = ContextRuntime(db)
        assert isinstance(runtime.budget, ContextBudgetEnforcer)
        assert isinstance(runtime.ranker, ContextItemRanker)
        assert isinstance(runtime.sanitizer, ContextItemSanitizer)

    async def test_assemble_delegates(self, db: AsyncSession):
        runtime = ContextRuntime(db)
        items = [_item(token_count=10) for _ in range(2)]
        inp = _assembly_input(budget=100)
        result = await runtime.assemble(inp, items)
        assert result.snapshot_id is not None
        assert result.window.total_tokens == 20

    async def test_reconstruct_delegates(self, db: AsyncSession):
        runtime = ContextRuntime(db)
        items = [_item(token_count=5)]
        inp = _assembly_input(budget=100)
        assembled = await runtime.assemble(inp, items)
        reconstructed = await runtime.reconstruct(assembled.snapshot_id)
        assert reconstructed.snapshot_id == assembled.snapshot_id

    async def test_reconstruct_by_key_delegates(self, db: AsyncSession):
        runtime = ContextRuntime(db)
        items = [_item(token_count=5)]
        inp = _assembly_input(budget=100)
        await runtime.assemble(inp, items)
        reconstructed = await runtime.reconstruct_by_key(inp.assembly_key)
        assert reconstructed.assembly_key == inp.assembly_key

    async def test_check_budget_passes(self, db: AsyncSession):
        runtime = ContextRuntime(db)
        runtime.check_budget(ContextBudgetLevel.agent, actual=50, budget=100)

    async def test_check_budget_raises(self, db: AsyncSession):
        runtime = ContextRuntime(db)
        with pytest.raises(ContextBudgetExceededError):
            runtime.check_budget(ContextBudgetLevel.agent, actual=200, budget=100)

    async def test_check_budget_scope_propagated(self, db: AsyncSession):
        runtime = ContextRuntime(db)
        with pytest.raises(ContextBudgetExceededError) as exc_info:
            runtime.check_budget(
                ContextBudgetLevel.call, actual=999, budget=100, scope="my-scope"
            )
        assert exc_info.value.scope == "my-scope"

    async def test_reconstruct_not_found_raises(self, db: AsyncSession):
        runtime = ContextRuntime(db)
        with pytest.raises(ContextReplayError):
            await runtime.reconstruct(uuid4())
