"""
Phase 8 — AI Runtime Foundation Tests.

Covers:
- AITaskInput / AIExecutionBounds / AITaskOutput / AIExecutionResult contracts
- TokenBudget primitives (consume, exhaust, utilization)
- AIProvider protocol + NoOpProvider
- ProviderRegistry (register, get, get_or_raise)
- AIExecutionContext (frozen, all fields)
- AIToolDefinition + AIToolRegistry (register, lookup, approval flag)
- SandboxPolicy + SandboxGuard (tool check, budget/timeout caps)
- AIExecutionRepository (get_by_key idempotency, get_by_workflow, get_by_status)
- AIExecutionRuntime lifecycle:
    create (idempotent), start, complete, fail (retry reset), fail (exhausted),
    cancel (idempotent, terminal guard), checkpoint, mark_awaiting_approval,
    resume_from_approval
- AIAuditRuntime (record, get_for_execution)
- AIApprovalGate (check_tool pass-through, requires_approval flow, resolve approve/reject)
- Domain events emitted at each lifecycle transition
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ai.audit import AIAuditRuntime
from ai.budget import BudgetExhaustedError, TokenBudget
from ai.context import AIExecutionContext
from ai.contracts import (
    AIExecutionBounds,
    AIExecutionResult,
    AITaskInput,
    AITaskOutput,
    AIToolCallRequest,
    AIToolCallResult,
)
from ai.gate import AIApprovalGate, AIApprovalGateError
from ai.lifecycle import (
    EVT_APPROVAL_REQUIRED,
    EVT_CANCELLED,
    EVT_CHECKPOINTED,
    EVT_COMPLETED,
    EVT_CREATED,
    EVT_FAILED,
    EVT_RESUMED,
    EVT_RETRY_SCHEDULED,
    EVT_STARTED,
    AIExecutionRuntime,
    AIExecutionStateError,
)
from ai.provider import AIProvider, NoOpProvider, ProviderRegistry, provider_registry
from ai.registry import (
    AIToolDefinition,
    AIToolRegistry,
    ToolNotFoundError,
)
from ai.sandbox import (
    PERMISSIVE_SANDBOX,
    RESTRICTED_SANDBOX,
    SandboxGuard,
    SandboxPolicy,
    SandboxViolationError,
)
from events.replay import replay_channel
from models.enums import (
    AIExecutionStatus,
    AIProviderType,
    AITaskType,
    ApprovalType,
    WorkflowType,
)
from repositories.ai_execution import AIExecutionRepository
from workflows.runtime import WorkflowRuntime

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _input(key: str | None = None) -> AITaskInput:
    return AITaskInput(
        task_type=AITaskType.inference,
        payload={"prompt": "hello"},
        execution_key=key or f"key-{uuid4()}",
        provider=AIProviderType.noop,
        model_name="noop",
    )


def _bounds() -> AIExecutionBounds:
    return AIExecutionBounds(token_budget=512, timeout_seconds=10, max_attempts=3)


def _ctx(key: str | None = None, workflow_id=None) -> AIExecutionContext:
    return AIExecutionContext(
        execution_id=uuid4(),
        execution_key=key or f"key-{uuid4()}",
        task_input=_input(key),
        bounds=_bounds(),
        workflow_id=workflow_id,
        correlation_id="corr-test",
    )


async def _workflow(db: AsyncSession):
    return await WorkflowRuntime(db).start(WorkflowType.outreach)


# ---------------------------------------------------------------------------
# 1. Contracts (frozen dataclasses)
# ---------------------------------------------------------------------------

class TestContracts:
    def test_task_input_frozen(self) -> None:
        inp = _input()
        with pytest.raises(Exception):
            inp.payload = {}  # type: ignore[misc]

    def test_bounds_defaults(self) -> None:
        b = AIExecutionBounds()
        assert b.token_budget == 4096
        assert b.timeout_seconds == 30
        assert b.max_attempts == 3

    def test_task_output_frozen(self) -> None:
        out = AITaskOutput(output={"x": 1}, tokens_used=10, model_name="noop")
        with pytest.raises(Exception):
            out.tokens_used = 99  # type: ignore[misc]

    def test_execution_result_frozen(self) -> None:
        r = AIExecutionResult(
            execution_id=uuid4(),
            execution_key="k",
            status=AIExecutionStatus.pending,
            output=None,
            tokens_used=None,
            attempt=0,
        )
        with pytest.raises(Exception):
            r.status = AIExecutionStatus.completed  # type: ignore[misc]

    def test_tool_call_request_frozen(self) -> None:
        req = AIToolCallRequest(
            execution_id=uuid4(),
            tool_id="t",
            tool_input={},
            call_key="ck",
        )
        with pytest.raises(Exception):
            req.tool_id = "other"  # type: ignore[misc]

    def test_tool_call_result_defaults(self) -> None:
        r = AIToolCallResult(
            execution_id=uuid4(),
            tool_id="t",
            call_key="ck",
            output={},
        )
        assert r.approved is True
        assert r.error is None


# ---------------------------------------------------------------------------
# 2. TokenBudget
# ---------------------------------------------------------------------------

class TestTokenBudget:
    def test_consume_within_limit(self) -> None:
        b = TokenBudget(limit=100)
        b.consume(40)
        assert b.used == 40
        assert b.remaining == 60

    def test_consume_exact_limit(self) -> None:
        b = TokenBudget(limit=100)
        b.consume(100)
        assert b.is_exhausted

    def test_consume_over_limit_raises(self) -> None:
        b = TokenBudget(limit=100)
        b.consume(60)
        with pytest.raises(BudgetExhaustedError) as exc_info:
            b.consume(50)
        assert exc_info.value.requested == 50
        assert exc_info.value.remaining == 40

    def test_utilization(self) -> None:
        b = TokenBudget(limit=200, used=50)
        assert b.utilization == 0.25

    def test_zero_limit_utilization(self) -> None:
        b = TokenBudget(limit=0)
        assert b.utilization == 1.0

    def test_negative_consume_raises(self) -> None:
        b = TokenBudget(limit=100)
        with pytest.raises(ValueError):
            b.consume(-1)

    def test_remaining_never_negative(self) -> None:
        b = TokenBudget(limit=10, used=10)
        assert b.remaining == 0


# ---------------------------------------------------------------------------
# 3. AIProvider + ProviderRegistry
# ---------------------------------------------------------------------------

class TestProvider:
    def test_noop_provider_satisfies_protocol(self) -> None:
        noop = NoOpProvider()
        assert isinstance(noop, AIProvider)

    @pytest.mark.asyncio
    async def test_noop_returns_empty_output(self) -> None:
        noop = NoOpProvider()
        out = await noop.execute(_ctx())
        assert out.tokens_used == 0
        assert out.output == {}
        assert out.model_name == "noop"

    def test_registry_noop_pre_registered(self) -> None:
        p = provider_registry.get("noop")
        assert p is not None

    def test_registry_get_or_raise_unknown(self) -> None:
        with pytest.raises(KeyError):
            provider_registry.get_or_raise("nonexistent_provider_xyz")

    def test_registry_register_and_get(self) -> None:
        reg = ProviderRegistry()
        reg.register("noop", NoOpProvider())
        assert reg.get("noop") is not None

    def test_registry_overwrite(self) -> None:
        reg = ProviderRegistry()
        p1 = NoOpProvider()
        p2 = NoOpProvider()
        reg.register("x", p1)
        reg.register("x", p2)
        assert reg.get("x") is p2


# ---------------------------------------------------------------------------
# 4. AIExecutionContext
# ---------------------------------------------------------------------------

class TestExecutionContext:
    def test_context_frozen(self) -> None:
        ctx = _ctx()
        with pytest.raises(Exception):
            ctx.execution_key = "mutated"  # type: ignore[misc]

    def test_context_optional_fields_default_none(self) -> None:
        ctx = _ctx()
        assert ctx.workflow_id is None
        assert ctx.actor_id is None
        assert ctx.checkpoint_state is None


# ---------------------------------------------------------------------------
# 5. AIToolRegistry
# ---------------------------------------------------------------------------

class TestToolRegistry:
    def test_register_and_get(self) -> None:
        reg = AIToolRegistry()
        t = AIToolDefinition(
            tool_id="fetch_lead",
            name="Fetch Lead",
            description="Fetches lead data",
            input_schema={"type": "object"},
        )
        reg.register(t)
        assert reg.get("fetch_lead") is t

    def test_get_or_raise_missing(self) -> None:
        reg = AIToolRegistry()
        with pytest.raises(ToolNotFoundError):
            reg.get_or_raise("not_there")

    def test_requires_approval_flag(self) -> None:
        reg = AIToolRegistry()
        reg.register(AIToolDefinition(
            tool_id="dangerous",
            name="Dangerous",
            description="",
            input_schema={},
            requires_approval=True,
            approval_type=ApprovalType.outreach,
        ))
        assert reg.requires_approval("dangerous") is True
        assert reg.requires_approval("unknown_tool") is False

    def test_unregister(self) -> None:
        reg = AIToolRegistry()
        reg.register(AIToolDefinition(tool_id="t", name="T", description="", input_schema={}))
        reg.unregister("t")
        assert reg.get("t") is None

    def test_all_returns_all_tools(self) -> None:
        reg = AIToolRegistry()
        reg.register(AIToolDefinition(tool_id="a", name="A", description="", input_schema={}))
        reg.register(AIToolDefinition(tool_id="b", name="B", description="", input_schema={}))
        ids = {t.tool_id for t in reg.all()}
        assert {"a", "b"} == ids

    def test_tool_definition_frozen(self) -> None:
        t = AIToolDefinition(tool_id="x", name="X", description="", input_schema={})
        with pytest.raises(Exception):
            t.tool_id = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6. SandboxGuard
# ---------------------------------------------------------------------------

class TestSandbox:
    def test_restricted_blocks_unsafe_tool(self) -> None:
        reg = AIToolRegistry()
        reg.register(AIToolDefinition(
            tool_id="bad",
            name="Bad",
            description="",
            input_schema={},
            is_sandbox_safe=False,
        ))
        guard = SandboxGuard(RESTRICTED_SANDBOX, registry=reg)
        with pytest.raises(SandboxViolationError, match="sandbox-safe"):
            guard.check_tool("bad")

    def test_restricted_passes_safe_tool(self) -> None:
        reg = AIToolRegistry()
        reg.register(AIToolDefinition(
            tool_id="safe",
            name="Safe",
            description="",
            input_schema={},
            is_sandbox_safe=True,
        ))
        guard = SandboxGuard(RESTRICTED_SANDBOX, registry=reg)
        guard.check_tool("safe")  # should not raise

    def test_allowlist_blocks_unlisted_tool(self) -> None:
        policy = SandboxPolicy(allowed_tool_ids=frozenset({"allowed_tool"}))
        guard = SandboxGuard(policy)
        with pytest.raises(SandboxViolationError, match="allowlist"):
            guard.check_tool("other_tool")

    def test_allowlist_permits_listed_tool(self) -> None:
        policy = SandboxPolicy(allowed_tool_ids=frozenset({"t"}))
        guard = SandboxGuard(policy)
        guard.check_tool("t")  # no raise

    def test_budget_cap(self) -> None:
        guard = SandboxGuard(RESTRICTED_SANDBOX)
        with pytest.raises(SandboxViolationError, match="token budget"):
            guard.check_budget(99999)

    def test_timeout_cap(self) -> None:
        guard = SandboxGuard(RESTRICTED_SANDBOX)
        with pytest.raises(SandboxViolationError, match="timeout"):
            guard.check_timeout(9999)

    def test_effective_budget_clamps(self) -> None:
        policy = SandboxPolicy(max_token_budget=100)
        guard = SandboxGuard(policy)
        assert guard.effective_budget(200) == 100
        assert guard.effective_budget(50) == 50

    def test_effective_timeout_clamps(self) -> None:
        policy = SandboxPolicy(max_timeout_seconds=60)
        guard = SandboxGuard(policy)
        assert guard.effective_timeout(120) == 60
        assert guard.effective_timeout(30) == 30

    def test_permissive_sandbox_allows_unsafe(self) -> None:
        reg = AIToolRegistry()
        reg.register(AIToolDefinition(
            tool_id="unsafe",
            name="Unsafe",
            description="",
            input_schema={},
            is_sandbox_safe=False,
        ))
        guard = SandboxGuard(PERMISSIVE_SANDBOX, registry=reg)
        guard.check_tool("unsafe")  # no raise


# ---------------------------------------------------------------------------
# 7. AIExecutionRepository
# ---------------------------------------------------------------------------

class TestAIExecutionRepository:
    @pytest.mark.asyncio
    async def test_get_by_key_returns_none_if_missing(self, db: AsyncSession) -> None:
        repo = AIExecutionRepository(db)
        assert await repo.get_by_key("nonexistent-key") is None

    @pytest.mark.asyncio
    async def test_get_by_id_or_raise_missing(self, db: AsyncSession) -> None:
        repo = AIExecutionRepository(db)
        with pytest.raises(ValueError, match="not found"):
            await repo.get_by_id_or_raise(uuid4())

    @pytest.mark.asyncio
    async def test_get_by_workflow(self, db: AsyncSession) -> None:
        wf = await _workflow(db)
        rt = AIExecutionRuntime(db)
        ctx = AIExecutionContext(
            execution_id=uuid4(),
            execution_key=f"k-{uuid4()}",
            task_input=_input(),
            bounds=_bounds(),
            workflow_id=wf.id,
        )
        await rt.create(ctx)
        repo = AIExecutionRepository(db)
        rows = await repo.get_by_workflow(wf.id)
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_get_by_status(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        ctx = _ctx()
        await rt.create(ctx)
        repo = AIExecutionRepository(db)
        pending = await repo.get_by_status(AIExecutionStatus.pending)
        keys = [r.execution_key for r in pending]
        assert ctx.execution_key in keys


# ---------------------------------------------------------------------------
# 8. AIExecutionRuntime — lifecycle
# ---------------------------------------------------------------------------

class TestAIExecutionLifecycle:
    @pytest.mark.asyncio
    async def test_create_new_execution(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        result = await rt.create(_ctx())
        assert result.status == AIExecutionStatus.pending
        assert result.attempt == 0

    @pytest.mark.asyncio
    async def test_create_idempotent(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        key = f"idem-{uuid4()}"
        ctx = _ctx(key=key)
        r1 = await rt.create(ctx)
        r2 = await rt.create(ctx)
        assert r1.execution_id == r2.execution_id

    @pytest.mark.asyncio
    async def test_create_emits_event(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        ctx = _ctx()
        await rt.create(ctx)
        events, _ = await replay_channel(db, "ai")
        types = [e.event_type for e in events]
        assert EVT_CREATED in types

    @pytest.mark.asyncio
    async def test_start_pending_to_running(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        started = await rt.start(r.execution_id)
        assert started.status == AIExecutionStatus.running
        assert started.attempt == 1

    @pytest.mark.asyncio
    async def test_start_emits_event(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        await rt.start(r.execution_id)
        events, _ = await replay_channel(db, "ai")
        types = [e.event_type for e in events]
        assert EVT_STARTED in types

    @pytest.mark.asyncio
    async def test_start_non_pending_raises(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        await rt.start(r.execution_id)
        with pytest.raises(AIExecutionStateError):
            await rt.start(r.execution_id)

    @pytest.mark.asyncio
    async def test_complete_running(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        await rt.start(r.execution_id)
        done = await rt.complete(r.execution_id, output={"result": "ok"}, tokens_used=42)
        assert done.status == AIExecutionStatus.completed
        assert done.tokens_used == 42
        assert done.output == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_complete_emits_event(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        await rt.start(r.execution_id)
        await rt.complete(r.execution_id, output={}, tokens_used=5)
        events, _ = await replay_channel(db, "ai")
        types = [e.event_type for e in events]
        assert EVT_COMPLETED in types

    @pytest.mark.asyncio
    async def test_complete_non_running_raises(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        with pytest.raises(AIExecutionStateError):
            await rt.complete(r.execution_id, output={}, tokens_used=0)

    @pytest.mark.asyncio
    async def test_fail_with_retry_resets_to_pending(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        # max_attempts=3, attempt will be 1 after start → retry eligible
        ctx = AIExecutionContext(
            execution_id=uuid4(),
            execution_key=f"k-{uuid4()}",
            task_input=_input(),
            bounds=AIExecutionBounds(max_attempts=3),
        )
        r = await rt.create(ctx)
        await rt.start(r.execution_id)
        failed = await rt.fail(r.execution_id, error="boom")
        assert failed.status == AIExecutionStatus.pending

    @pytest.mark.asyncio
    async def test_fail_retry_emits_retry_scheduled(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        ctx = AIExecutionContext(
            execution_id=uuid4(),
            execution_key=f"k-{uuid4()}",
            task_input=_input(),
            bounds=AIExecutionBounds(max_attempts=3),
        )
        r = await rt.create(ctx)
        await rt.start(r.execution_id)
        await rt.fail(r.execution_id, error="boom")
        events, _ = await replay_channel(db, "ai")
        types = [e.event_type for e in events]
        assert EVT_RETRY_SCHEDULED in types

    @pytest.mark.asyncio
    async def test_fail_exhausted_sets_failed(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        ctx = AIExecutionContext(
            execution_id=uuid4(),
            execution_key=f"k-{uuid4()}",
            task_input=_input(),
            bounds=AIExecutionBounds(max_attempts=1),
        )
        r = await rt.create(ctx)
        await rt.start(r.execution_id)
        failed = await rt.fail(r.execution_id, error="exhausted")
        assert failed.status == AIExecutionStatus.failed

    @pytest.mark.asyncio
    async def test_fail_exhausted_emits_failed(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        ctx = AIExecutionContext(
            execution_id=uuid4(),
            execution_key=f"k-{uuid4()}",
            task_input=_input(),
            bounds=AIExecutionBounds(max_attempts=1),
        )
        r = await rt.create(ctx)
        await rt.start(r.execution_id)
        await rt.fail(r.execution_id, error="exhausted")
        events, _ = await replay_channel(db, "ai")
        types = [e.event_type for e in events]
        assert EVT_FAILED in types

    @pytest.mark.asyncio
    async def test_cancel_pending(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        cancelled = await rt.cancel(r.execution_id, reason="user_request")
        assert cancelled.status == AIExecutionStatus.cancelled

    @pytest.mark.asyncio
    async def test_cancel_running(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        await rt.start(r.execution_id)
        cancelled = await rt.cancel(r.execution_id, reason="timeout")
        assert cancelled.status == AIExecutionStatus.cancelled

    @pytest.mark.asyncio
    async def test_cancel_idempotent_on_completed(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        await rt.start(r.execution_id)
        await rt.complete(r.execution_id, output={}, tokens_used=0)
        # Cancel on completed → no-op
        result = await rt.cancel(r.execution_id)
        assert result.status == AIExecutionStatus.completed

    @pytest.mark.asyncio
    async def test_cancel_emits_event(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        await rt.cancel(r.execution_id, reason="test")
        events, _ = await replay_channel(db, "ai")
        types = [e.event_type for e in events]
        assert EVT_CANCELLED in types

    @pytest.mark.asyncio
    async def test_checkpoint_saves_state(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        await rt.start(r.execution_id)
        await rt.checkpoint(r.execution_id, state={"step": "step_1", "data": 42})
        # verify persisted
        repo = AIExecutionRepository(db)
        row = await repo.get_by_id_or_raise(r.execution_id)
        assert row.checkpoint_state == {"step": "step_1", "data": 42}

    @pytest.mark.asyncio
    async def test_checkpoint_emits_event(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        await rt.start(r.execution_id)
        await rt.checkpoint(r.execution_id, state={"x": 1})
        events, _ = await replay_channel(db, "ai")
        types = [e.event_type for e in events]
        assert EVT_CHECKPOINTED in types

    @pytest.mark.asyncio
    async def test_checkpoint_non_running_raises(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        with pytest.raises(AIExecutionStateError):
            await rt.checkpoint(r.execution_id, state={})

    @pytest.mark.asyncio
    async def test_mark_awaiting_approval(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        await rt.start(r.execution_id)
        paused = await rt.mark_awaiting_approval(r.execution_id, approval_id=uuid4())
        assert paused.status == AIExecutionStatus.awaiting_approval

    @pytest.mark.asyncio
    async def test_awaiting_approval_emits_event(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        await rt.start(r.execution_id)
        await rt.mark_awaiting_approval(r.execution_id, approval_id=uuid4())
        events, _ = await replay_channel(db, "ai")
        types = [e.event_type for e in events]
        assert EVT_APPROVAL_REQUIRED in types

    @pytest.mark.asyncio
    async def test_resume_from_approval(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        await rt.start(r.execution_id)
        await rt.mark_awaiting_approval(r.execution_id, approval_id=uuid4())
        resumed = await rt.resume_from_approval(r.execution_id)
        assert resumed.status == AIExecutionStatus.running

    @pytest.mark.asyncio
    async def test_resume_emits_event(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        await rt.start(r.execution_id)
        await rt.mark_awaiting_approval(r.execution_id, approval_id=uuid4())
        await rt.resume_from_approval(r.execution_id)
        events, _ = await replay_channel(db, "ai")
        types = [e.event_type for e in events]
        assert EVT_RESUMED in types

    @pytest.mark.asyncio
    async def test_resume_from_wrong_state_raises(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        await rt.start(r.execution_id)
        with pytest.raises(AIExecutionStateError):
            await rt.resume_from_approval(r.execution_id)


# ---------------------------------------------------------------------------
# 9. AIAuditRuntime
# ---------------------------------------------------------------------------

class TestAIAuditRuntime:
    @pytest.mark.asyncio
    async def test_record_appends_entry(self, db: AsyncSession) -> None:
        execution_id = uuid4()
        audit = AIAuditRuntime(db)
        entry = await audit.record(
            execution_id=execution_id,
            action="execution_started",
            payload={"attempt": 1},
        )
        assert entry.execution_id == execution_id
        assert entry.action == "execution_started"

    @pytest.mark.asyncio
    async def test_get_for_execution_ordered(self, db: AsyncSession) -> None:
        execution_id = uuid4()
        audit = AIAuditRuntime(db)
        await audit.record(execution_id, "first", {})
        await audit.record(execution_id, "second", {})
        entries = await audit.get_for_execution(execution_id)
        assert len(entries) == 2
        assert entries[0].action == "first"
        assert entries[1].action == "second"

    @pytest.mark.asyncio
    async def test_get_for_execution_empty(self, db: AsyncSession) -> None:
        audit = AIAuditRuntime(db)
        entries = await audit.get_for_execution(uuid4())
        assert entries == []

    @pytest.mark.asyncio
    async def test_entries_are_immutable_after_write(self, db: AsyncSession) -> None:
        execution_id = uuid4()
        audit = AIAuditRuntime(db)
        entry = await audit.record(execution_id, "test_action", {"k": "v"})
        with pytest.raises(Exception):
            entry.action = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 10. AIApprovalGate
# ---------------------------------------------------------------------------

class TestAIApprovalGate:
    @pytest.mark.asyncio
    async def test_check_tool_no_approval_needed(self, db: AsyncSession) -> None:
        reg = AIToolRegistry()
        reg.register(AIToolDefinition(
            tool_id="safe_tool",
            name="Safe",
            description="",
            input_schema={},
            requires_approval=False,
        ))
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        gate = AIApprovalGate(db, registry=reg)
        can_proceed = await gate.check_tool(r.execution_id, "safe_tool")
        assert can_proceed is True

    @pytest.mark.asyncio
    async def test_check_unknown_tool_passes(self, db: AsyncSession) -> None:
        reg = AIToolRegistry()
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        await rt.start(r.execution_id)
        gate = AIApprovalGate(db, registry=reg)
        # Unknown tool → no approval required → pass
        can_proceed = await gate.check_tool(r.execution_id, "unknown")
        assert can_proceed is True

    @pytest.mark.asyncio
    async def test_check_tool_requires_approval_pauses(self, db: AsyncSession) -> None:
        wf = await _workflow(db)
        reg = AIToolRegistry()
        reg.register(AIToolDefinition(
            tool_id="gated_tool",
            name="Gated",
            description="",
            input_schema={},
            requires_approval=True,
            approval_type=ApprovalType.outreach,
        ))
        rt = AIExecutionRuntime(db)
        ctx = AIExecutionContext(
            execution_id=uuid4(),
            execution_key=f"k-{uuid4()}",
            task_input=_input(),
            bounds=_bounds(),
            workflow_id=wf.id,
        )
        r = await rt.create(ctx)
        await rt.start(r.execution_id)
        gate = AIApprovalGate(db, registry=reg)
        can_proceed = await gate.check_tool(
            r.execution_id, "gated_tool", workflow_id=wf.id
        )
        assert can_proceed is False
        # execution should be awaiting approval
        repo = AIExecutionRepository(db)
        row = await repo.get_by_id_or_raise(r.execution_id)
        assert row.status == AIExecutionStatus.awaiting_approval

    @pytest.mark.asyncio
    async def test_check_tool_requires_approval_no_workflow_raises(
        self, db: AsyncSession
    ) -> None:
        reg = AIToolRegistry()
        reg.register(AIToolDefinition(
            tool_id="gated2",
            name="Gated2",
            description="",
            input_schema={},
            requires_approval=True,
            approval_type=ApprovalType.outreach,
        ))
        rt = AIExecutionRuntime(db)
        r = await rt.create(_ctx())
        await rt.start(r.execution_id)
        gate = AIApprovalGate(db, registry=reg)
        with pytest.raises(AIApprovalGateError, match="workflow_id"):
            await gate.check_tool(r.execution_id, "gated2", workflow_id=None)

    @pytest.mark.asyncio
    async def test_resolve_approve_resumes_execution(self, db: AsyncSession) -> None:
        wf = await _workflow(db)
        reg = AIToolRegistry()
        reg.register(AIToolDefinition(
            tool_id="gt",
            name="GT",
            description="",
            input_schema={},
            requires_approval=True,
            approval_type=ApprovalType.outreach,
        ))
        rt = AIExecutionRuntime(db)
        ctx = AIExecutionContext(
            execution_id=uuid4(),
            execution_key=f"k-{uuid4()}",
            task_input=_input(),
            bounds=_bounds(),
            workflow_id=wf.id,
        )
        r = await rt.create(ctx)
        await rt.start(r.execution_id)
        gate = AIApprovalGate(db, registry=reg)
        await gate.check_tool(r.execution_id, "gt", workflow_id=wf.id)
        # retrieve approval_id from row
        repo = AIExecutionRepository(db)
        row = await repo.get_by_id_or_raise(r.execution_id)
        approval_id = row.approval_id
        await gate.resolve(r.execution_id, approval_id, approved=True)
        row2 = await repo.get_by_id_or_raise(r.execution_id)
        assert row2.status == AIExecutionStatus.running

    @pytest.mark.asyncio
    async def test_resolve_reject_cancels_execution(self, db: AsyncSession) -> None:
        wf = await _workflow(db)
        reg = AIToolRegistry()
        reg.register(AIToolDefinition(
            tool_id="gt2",
            name="GT2",
            description="",
            input_schema={},
            requires_approval=True,
            approval_type=ApprovalType.outreach,
        ))
        rt = AIExecutionRuntime(db)
        ctx = AIExecutionContext(
            execution_id=uuid4(),
            execution_key=f"k-{uuid4()}",
            task_input=_input(),
            bounds=_bounds(),
            workflow_id=wf.id,
        )
        r = await rt.create(ctx)
        await rt.start(r.execution_id)
        gate = AIApprovalGate(db, registry=reg)
        await gate.check_tool(r.execution_id, "gt2", workflow_id=wf.id)
        repo = AIExecutionRepository(db)
        row = await repo.get_by_id_or_raise(r.execution_id)
        await gate.resolve(r.execution_id, row.approval_id, approved=False)
        row2 = await repo.get_by_id_or_raise(r.execution_id)
        assert row2.status == AIExecutionStatus.cancelled


# ---------------------------------------------------------------------------
# 11. Full lifecycle integration
# ---------------------------------------------------------------------------

class TestFullLifecycle:
    @pytest.mark.asyncio
    async def test_happy_path_with_noop_provider(self, db: AsyncSession) -> None:
        """create → start → (noop execute) → complete — full path."""
        rt = AIExecutionRuntime(db)
        ctx = _ctx()
        r = await rt.create(ctx)
        assert r.status == AIExecutionStatus.pending

        await rt.start(r.execution_id)
        noop = NoOpProvider()
        out = await noop.execute(ctx)

        done = await rt.complete(r.execution_id, output=out.output, tokens_used=out.tokens_used)
        assert done.status == AIExecutionStatus.completed
        assert done.tokens_used == 0

    @pytest.mark.asyncio
    async def test_checkpoint_then_resume_on_retry(self, db: AsyncSession) -> None:
        """fail (retry) → checkpoint survives → can complete next attempt."""
        rt = AIExecutionRuntime(db)
        ctx = AIExecutionContext(
            execution_id=uuid4(),
            execution_key=f"k-{uuid4()}",
            task_input=_input(),
            bounds=AIExecutionBounds(max_attempts=2),
        )
        r = await rt.create(ctx)
        await rt.start(r.execution_id)
        await rt.checkpoint(r.execution_id, state={"progress": "step1_done"})
        # fail attempt 1 → back to pending
        await rt.fail(r.execution_id, error="transient error")
        repo = AIExecutionRepository(db)
        row = await repo.get_by_id_or_raise(r.execution_id)
        assert row.status == AIExecutionStatus.pending
        # checkpoint preserved
        assert row.checkpoint_state == {"progress": "step1_done"}
        # retry: start again, complete
        await rt.start(r.execution_id)
        done = await rt.complete(r.execution_id, output={"final": True}, tokens_used=10)
        assert done.status == AIExecutionStatus.completed

    @pytest.mark.asyncio
    async def test_all_events_emitted_in_happy_path(self, db: AsyncSession) -> None:
        rt = AIExecutionRuntime(db)
        ctx = _ctx()
        r = await rt.create(ctx)
        await rt.start(r.execution_id)
        await rt.complete(r.execution_id, output={}, tokens_used=1)
        events, _ = await replay_channel(db, "ai")
        types = {e.event_type for e in events}
        assert {EVT_CREATED, EVT_STARTED, EVT_COMPLETED} <= types
