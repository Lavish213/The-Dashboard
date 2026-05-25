"""
Phase 13 — Research Runtime tests.

All tests use SAVEPOINT isolation (db fixture).
Deterministic replay tests verify event ordering.
No external APIs, no embeddings, no autonomous behavior.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import (
    ResearchEvidenceStatus,
    ResearchJobStatus,
    ResearchMemoryScope,
    ResearchPlanStatus,
    ResearchTaskStatus,
)
from research.contracts import (
    ResearchEvidenceSpec,
    ResearchGraphSpec,
    ResearchJobSpec,
    ResearchMemorySpec,
    ResearchPlanRevision,
    ResearchPlanSpec,
    ResearchSafetyConfig,
    ResearchTaskDependencySpec,
    ResearchTaskSpec,
)
from research.evidence import ResearchEvidenceRuntime
from research.graph import ResearchCycleError, ResearchTaskGraph
from research.job import ResearchJobError, ResearchJobRuntime
from research.memory import ResearchMemoryRuntime
from research.plan import ResearchPlanError, ResearchPlanRuntime
from research.replay import ResearchReplayRuntime
from research.safety import (
    ResearchBudgetExceededError,
    ResearchDepthExceededError,
    ResearchSafetyRuntime,
)
from research.task import (
    ResearchTaskError,
    ResearchTaskRetryExhaustedError,
    ResearchTaskRuntime,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _job_spec(**kwargs) -> ResearchJobSpec:
    return ResearchJobSpec(
        job_key=kwargs.get("job_key", f"job-{uuid.uuid4()}"),
        token_budget=kwargs.get("token_budget", 4096),
        max_depth=kwargs.get("max_depth", 5),
    )


def _task_spec(job_id: uuid.UUID, index: int = 0, **kwargs) -> ResearchTaskSpec:
    return ResearchTaskSpec(
        job_id=job_id,
        task_index=index,
        task_type=kwargs.get("task_type", "search"),
        input_payload=kwargs.get("input_payload", {"query": "test"}),
        depth=kwargs.get("depth", 0),
        max_retries=kwargs.get("max_retries", 2),
        task_key=kwargs.get("task_key"),
    )


def _evidence_spec(job_id: uuid.UUID, content: str = "test", **kwargs) -> ResearchEvidenceSpec:
    content_hash = ResearchEvidenceRuntime.compute_hash(content)
    return ResearchEvidenceSpec(
        job_id=job_id,
        source_uri=f"https://example.com/{uuid.uuid4()}",
        source_type="web",
        content_hash=content_hash,
        provenance={"collector": "test", "collected_at": datetime.now(UTC).isoformat()},
        snapshot={"content": content},
        score=kwargs.get("score", 0.8),
        content_snippet=content[:100],
    )


# ---------------------------------------------------------------------------
# ResearchJobRuntime
# ---------------------------------------------------------------------------


class TestResearchJobRuntime:
    async def test_create_job(self, db: AsyncSession) -> None:
        rt = ResearchJobRuntime(db)
        spec = _job_spec()
        record = await rt.create(spec)

        assert record.job_key == spec.job_key
        assert record.status == ResearchJobStatus.queued
        assert record.token_budget == 4096
        assert record.tokens_used == 0
        assert record.task_count == 0

    async def test_create_idempotent(self, db: AsyncSession) -> None:
        rt = ResearchJobRuntime(db)
        spec = _job_spec()
        r1 = await rt.create(spec)
        r2 = await rt.create(spec)
        assert r1.job_id == r2.job_id

    async def test_start_job(self, db: AsyncSession) -> None:
        rt = ResearchJobRuntime(db)
        record = await rt.create(_job_spec())
        started = await rt.start(record.job_id)

        assert started.status == ResearchJobStatus.running
        assert started.started_at is not None

    async def test_pause_resume_cycle(self, db: AsyncSession) -> None:
        rt = ResearchJobRuntime(db)
        r = await rt.create(_job_spec())
        r = await rt.start(r.job_id)
        checkpoint = {"step": 3, "results": [1, 2, 3]}
        r = await rt.pause(r.job_id, checkpoint_state=checkpoint)

        assert r.status == ResearchJobStatus.paused
        assert r.checkpoint_state == checkpoint

        r = await rt.resume(r.job_id)
        assert r.status == ResearchJobStatus.running
        assert r.paused_at is None

    async def test_complete_job(self, db: AsyncSession) -> None:
        rt = ResearchJobRuntime(db)
        r = await rt.create(_job_spec())
        r = await rt.start(r.job_id)
        r = await rt.complete(r.job_id)

        assert r.status == ResearchJobStatus.completed
        assert r.completed_at is not None

    async def test_fail_job(self, db: AsyncSession) -> None:
        rt = ResearchJobRuntime(db)
        r = await rt.create(_job_spec())
        r = await rt.start(r.job_id)
        r = await rt.fail(r.job_id, error="something went wrong")

        assert r.status == ResearchJobStatus.failed
        assert r.error == "something went wrong"

    async def test_cancel_queued_job(self, db: AsyncSession) -> None:
        rt = ResearchJobRuntime(db)
        r = await rt.create(_job_spec())
        r = await rt.cancel(r.job_id, reason="user cancelled")

        assert r.status == ResearchJobStatus.cancelled
        assert r.cancel_reason == "user cancelled"
        assert r.cancelled_at is not None

    async def test_cancel_running_job(self, db: AsyncSession) -> None:
        rt = ResearchJobRuntime(db)
        r = await rt.create(_job_spec())
        r = await rt.start(r.job_id)
        r = await rt.cancel(r.job_id, reason="timeout")

        assert r.status == ResearchJobStatus.cancelled

    async def test_invalid_transition_raises(self, db: AsyncSession) -> None:
        rt = ResearchJobRuntime(db)
        r = await rt.create(_job_spec())
        r = await rt.start(r.job_id)
        r = await rt.complete(r.job_id)

        with pytest.raises(ResearchJobError, match="Invalid job transition"):
            await rt.start(r.job_id)

    async def test_completed_is_terminal(self, db: AsyncSession) -> None:
        rt = ResearchJobRuntime(db)
        r = await rt.create(_job_spec())
        r = await rt.start(r.job_id)
        r = await rt.complete(r.job_id)

        with pytest.raises(ResearchJobError):
            await rt.cancel(r.job_id, reason="late cancel")

    async def test_checkpoint_without_status_change(self, db: AsyncSession) -> None:
        rt = ResearchJobRuntime(db)
        r = await rt.create(_job_spec())
        r = await rt.start(r.job_id)
        r = await rt.checkpoint(r.job_id, {"cursor": 42})

        assert r.status == ResearchJobStatus.running
        assert r.checkpoint_state == {"cursor": 42}

    async def test_get_by_key(self, db: AsyncSession) -> None:
        rt = ResearchJobRuntime(db)
        spec = _job_spec()
        created = await rt.create(spec)
        fetched = await rt.get_by_key(spec.job_key)

        assert fetched is not None
        assert fetched.job_id == created.job_id

    async def test_get_missing_returns_none(self, db: AsyncSession) -> None:
        rt = ResearchJobRuntime(db)
        result = await rt.get(uuid.uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# ResearchTaskRuntime
# ---------------------------------------------------------------------------


class TestResearchTaskRuntime:
    async def _make_job(self, db: AsyncSession) -> uuid.UUID:
        rt = ResearchJobRuntime(db)
        r = await rt.create(_job_spec())
        r = await rt.start(r.job_id)
        return r.job_id

    async def test_create_task(self, db: AsyncSession) -> None:
        job_id = await self._make_job(db)
        rt = ResearchTaskRuntime(db)
        spec = _task_spec(job_id)
        task = await rt.create(spec)

        assert task.job_id == job_id
        assert task.status == ResearchTaskStatus.pending
        assert task.task_type == "search"
        assert task.retry_count == 0

    async def test_create_idempotent_on_task_key(self, db: AsyncSession) -> None:
        job_id = await self._make_job(db)
        rt = ResearchTaskRuntime(db)
        spec = _task_spec(job_id, task_key="unique-task-key")
        t1 = await rt.create(spec)
        t2 = await rt.create(spec)
        assert t1.task_id == t2.task_id

    async def test_start_task(self, db: AsyncSession) -> None:
        job_id = await self._make_job(db)
        rt = ResearchTaskRuntime(db)
        task = await rt.create(_task_spec(job_id))
        task = await rt.start(task.task_id)

        assert task.status == ResearchTaskStatus.running
        assert task.started_at is not None

    async def test_complete_task_updates_job_counters(self, db: AsyncSession) -> None:
        job_id = await self._make_job(db)
        task_rt = ResearchTaskRuntime(db)
        job_rt = ResearchJobRuntime(db)

        task = await task_rt.create(_task_spec(job_id))
        task = await task_rt.start(task.task_id)
        task = await task_rt.complete(
            task.task_id,
            output_payload={"answer": 42},
            tokens_input=100,
            tokens_output=50,
        )

        assert task.status == ResearchTaskStatus.completed
        assert task.tokens_input == 100
        assert task.tokens_output == 50

        job = await job_rt.get(job_id)
        assert job is not None
        assert job.tokens_used == 150
        assert job.completed_task_count == 1

    async def test_fail_and_retry(self, db: AsyncSession) -> None:
        job_id = await self._make_job(db)
        rt = ResearchTaskRuntime(db)
        task = await rt.create(_task_spec(job_id, max_retries=2))
        task = await rt.start(task.task_id)
        task = await rt.fail(task.task_id, error="network error")

        assert task.status == ResearchTaskStatus.failed

        task = await rt.retry(task.task_id)
        assert task.status == ResearchTaskStatus.running
        assert task.retry_count == 1
        assert task.error is None

    async def test_retry_exhausted_raises(self, db: AsyncSession) -> None:
        job_id = await self._make_job(db)
        rt = ResearchTaskRuntime(db)
        task = await rt.create(_task_spec(job_id, max_retries=1))

        task = await rt.start(task.task_id)
        task = await rt.fail(task.task_id, error="err1")
        task = await rt.retry(task.task_id)
        task = await rt.fail(task.task_id, error="err2")

        with pytest.raises(ResearchTaskRetryExhaustedError):
            await rt.retry(task.task_id)

    async def test_cancel_pending_task(self, db: AsyncSession) -> None:
        job_id = await self._make_job(db)
        rt = ResearchTaskRuntime(db)
        task = await rt.create(_task_spec(job_id))
        task = await rt.cancel(task.task_id)

        assert task.status == ResearchTaskStatus.cancelled

    async def test_skip_task(self, db: AsyncSession) -> None:
        job_id = await self._make_job(db)
        rt = ResearchTaskRuntime(db)
        task = await rt.create(_task_spec(job_id))
        task = await rt.skip(task.task_id)

        assert task.status == ResearchTaskStatus.skipped

    async def test_completed_is_terminal(self, db: AsyncSession) -> None:
        job_id = await self._make_job(db)
        rt = ResearchTaskRuntime(db)
        task = await rt.create(_task_spec(job_id))
        task = await rt.start(task.task_id)
        task = await rt.complete(task.task_id, output_payload={})

        with pytest.raises(ResearchTaskError, match="Invalid task transition"):
            await rt.start(task.task_id)

    async def test_invalid_transition_raises(self, db: AsyncSession) -> None:
        job_id = await self._make_job(db)
        rt = ResearchTaskRuntime(db)
        task = await rt.create(_task_spec(job_id))

        with pytest.raises(ResearchTaskError, match="Invalid task transition"):
            await rt.complete(task.task_id, output_payload={})


# ---------------------------------------------------------------------------
# ResearchTaskGraph
# ---------------------------------------------------------------------------


class TestResearchTaskGraph:
    async def _make_running_job(self, db: AsyncSession) -> uuid.UUID:
        rt = ResearchJobRuntime(db)
        r = await rt.create(_job_spec())
        r = await rt.start(r.job_id)
        return r.job_id

    async def test_build_single_task(self, db: AsyncSession) -> None:
        job_id = await self._make_running_job(db)
        graph = ResearchTaskGraph(db)
        spec = ResearchGraphSpec(
            job_id=job_id,
            tasks=(ResearchTaskSpec(
                job_id=job_id,
                task_index=0,
                task_type="search",
                input_payload={"q": "test"},
            ),),
            dependencies=(),
        )
        records = await graph.build(spec)
        assert len(records) == 1
        assert records[0].task_type == "search"

    async def test_topological_order_linear_chain(self, db: AsyncSession) -> None:
        job_id = await self._make_running_job(db)
        graph = ResearchTaskGraph(db)
        task_rt = ResearchTaskRuntime(db)

        t0 = await task_rt.create(_task_spec(job_id, index=0))
        t1 = await task_rt.create(_task_spec(job_id, index=1))
        t2 = await task_rt.create(_task_spec(job_id, index=2))

        from repositories.research_task import ResearchTaskRepository  # noqa: PLC0415
        task_repo = ResearchTaskRepository(db)
        await task_repo.add_dependency(job_id, t0.task_id, t1.task_id)
        await task_repo.add_dependency(job_id, t1.task_id, t2.task_id)

        order = await graph.topological_order(job_id)

        assert len(order.task_indices) == 3
        idx_t0 = order.task_indices.index(0)
        idx_t1 = order.task_indices.index(1)
        idx_t2 = order.task_indices.index(2)
        assert idx_t0 < idx_t1 < idx_t2

    async def test_topological_order_parallel(self, db: AsyncSession) -> None:
        """Two independent tasks at level 0, one dependent at level 1."""
        job_id = await self._make_running_job(db)
        graph = ResearchTaskGraph(db)
        task_rt = ResearchTaskRuntime(db)

        t0 = await task_rt.create(_task_spec(job_id, index=0))
        t1 = await task_rt.create(_task_spec(job_id, index=1))
        t2 = await task_rt.create(_task_spec(job_id, index=2))

        from repositories.research_task import ResearchTaskRepository  # noqa: PLC0415
        task_repo = ResearchTaskRepository(db)
        await task_repo.add_dependency(job_id, t0.task_id, t2.task_id)
        await task_repo.add_dependency(job_id, t1.task_id, t2.task_id)

        order = await graph.topological_order(job_id)
        # t0 and t1 should come before t2
        idx_t2 = order.task_indices.index(2)
        assert idx_t2 == 2  # t2 is last

    async def test_cycle_detection_raises(self, db: AsyncSession) -> None:
        job_id = await self._make_running_job(db)
        task_rt = ResearchTaskRuntime(db)
        graph = ResearchTaskGraph(db)

        t0 = await task_rt.create(_task_spec(job_id, index=0))
        t1 = await task_rt.create(_task_spec(job_id, index=1))

        from repositories.research_task import ResearchTaskRepository  # noqa: PLC0415
        task_repo = ResearchTaskRepository(db)
        await task_repo.add_dependency(job_id, t0.task_id, t1.task_id)
        await task_repo.add_dependency(job_id, t1.task_id, t0.task_id)

        with pytest.raises(ResearchCycleError):
            await graph.topological_order(job_id)

    async def test_is_unblocked_no_deps(self, db: AsyncSession) -> None:
        job_id = await self._make_running_job(db)
        task_rt = ResearchTaskRuntime(db)
        graph = ResearchTaskGraph(db)

        t = await task_rt.create(_task_spec(job_id))
        assert await graph.is_unblocked(t.task_id) is True

    async def test_is_unblocked_with_incomplete_upstream(self, db: AsyncSession) -> None:
        job_id = await self._make_running_job(db)
        task_rt = ResearchTaskRuntime(db)
        graph = ResearchTaskGraph(db)

        t0 = await task_rt.create(_task_spec(job_id, index=0))
        t1 = await task_rt.create(_task_spec(job_id, index=1))

        from repositories.research_task import ResearchTaskRepository  # noqa: PLC0415
        await ResearchTaskRepository(db).add_dependency(job_id, t0.task_id, t1.task_id)

        assert await graph.is_unblocked(t1.task_id) is False

    async def test_is_unblocked_after_upstream_complete(self, db: AsyncSession) -> None:
        job_id = await self._make_running_job(db)
        task_rt = ResearchTaskRuntime(db)
        graph = ResearchTaskGraph(db)

        t0 = await task_rt.create(_task_spec(job_id, index=0))
        t1 = await task_rt.create(_task_spec(job_id, index=1))

        from repositories.research_task import ResearchTaskRepository  # noqa: PLC0415
        await ResearchTaskRepository(db).add_dependency(job_id, t0.task_id, t1.task_id)

        # Complete upstream
        t0 = await task_rt.start(t0.task_id)
        await task_rt.complete(t0.task_id, output_payload={})

        assert await graph.is_unblocked(t1.task_id) is True

    async def test_cycle_detection_in_spec(self, db: AsyncSession) -> None:
        """GraphSpec with cycle raises before any DB write."""
        job_id = await self._make_running_job(db)
        t0_id = uuid.uuid4()
        t1_id = uuid.uuid4()

        spec = ResearchGraphSpec(
            job_id=job_id,
            tasks=(),
            dependencies=(
                ResearchTaskDependencySpec(
                    job_id=job_id,
                    upstream_task_id=t0_id,
                    downstream_task_id=t1_id,
                ),
                ResearchTaskDependencySpec(
                    job_id=job_id,
                    upstream_task_id=t1_id,
                    downstream_task_id=t0_id,
                ),
            ),
        )
        graph = ResearchTaskGraph(db)
        with pytest.raises(ResearchCycleError):
            await graph.build(spec)


# ---------------------------------------------------------------------------
# ResearchEvidenceRuntime
# ---------------------------------------------------------------------------


class TestResearchEvidenceRuntime:
    async def _make_job_id(self, db: AsyncSession) -> uuid.UUID:
        rt = ResearchJobRuntime(db)
        r = await rt.create(_job_spec())
        r = await rt.start(r.job_id)
        return r.job_id

    async def test_record_evidence(self, db: AsyncSession) -> None:
        job_id = await self._make_job_id(db)
        rt = ResearchEvidenceRuntime(db)
        spec = _evidence_spec(job_id, "unique content A")
        rec = await rt.record(spec)

        assert rec.job_id == job_id
        assert rec.status == ResearchEvidenceStatus.pending
        assert rec.score == 0.8

    async def test_deduplication(self, db: AsyncSession) -> None:
        job_id = await self._make_job_id(db)
        rt = ResearchEvidenceRuntime(db)
        content = "duplicate content"
        spec = _evidence_spec(job_id, content)

        r1 = await rt.record(spec)
        r2 = await rt.record(spec)  # same hash → duplicate

        assert r1.evidence_id == r2.evidence_id
        assert r2.status == ResearchEvidenceStatus.duplicate

    async def test_accept_evidence(self, db: AsyncSession) -> None:
        job_id = await self._make_job_id(db)
        rt = ResearchEvidenceRuntime(db)
        rec = await rt.record(_evidence_spec(job_id, "content B"))
        rec = await rt.accept(rec.evidence_id)

        assert rec.status == ResearchEvidenceStatus.accepted

    async def test_reject_evidence(self, db: AsyncSession) -> None:
        job_id = await self._make_job_id(db)
        rt = ResearchEvidenceRuntime(db)
        rec = await rt.record(_evidence_spec(job_id, "content C"))
        rec = await rt.reject(rec.evidence_id, reason="irrelevant")

        assert rec.status == ResearchEvidenceStatus.rejected

    async def test_get_accepted(self, db: AsyncSession) -> None:
        job_id = await self._make_job_id(db)
        rt = ResearchEvidenceRuntime(db)

        r1 = await rt.record(_evidence_spec(job_id, "e1"))
        r2 = await rt.record(_evidence_spec(job_id, "e2"))
        await rt.record(_evidence_spec(job_id, "e3"))

        await rt.accept(r1.evidence_id)
        await rt.accept(r2.evidence_id)

        accepted = await rt.get_accepted(job_id)
        assert len(accepted) == 2

    async def test_compute_hash_deterministic(self) -> None:
        h1 = ResearchEvidenceRuntime.compute_hash("hello world")
        h2 = ResearchEvidenceRuntime.compute_hash("hello world")
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    async def test_compute_hash_dict_sorted(self) -> None:
        h1 = ResearchEvidenceRuntime.compute_hash({"b": 2, "a": 1})
        h2 = ResearchEvidenceRuntime.compute_hash({"a": 1, "b": 2})
        assert h1 == h2


# ---------------------------------------------------------------------------
# ResearchMemoryRuntime
# ---------------------------------------------------------------------------


class TestResearchMemoryRuntime:
    async def _make_job_id(self, db: AsyncSession) -> uuid.UUID:
        rt = ResearchJobRuntime(db)
        r = await rt.create(_job_spec())
        r = await rt.start(r.job_id)
        return r.job_id

    async def test_write_and_read(self, db: AsyncSession) -> None:
        job_id = await self._make_job_id(db)
        rt = ResearchMemoryRuntime(db)
        spec = ResearchMemorySpec(
            job_id=job_id,
            scope=ResearchMemoryScope.job,
            memory_key="facts",
            value={"items": [1, 2, 3]},
        )
        entry = await rt.write(spec)
        assert entry.memory_key == "facts"
        assert entry.value == {"items": [1, 2, 3]}
        assert entry.expires_at is None

        read = await rt.read(job_id, ResearchMemoryScope.job, "facts")
        assert read is not None
        assert read.value == {"items": [1, 2, 3]}

    async def test_overwrite_entry(self, db: AsyncSession) -> None:
        job_id = await self._make_job_id(db)
        rt = ResearchMemoryRuntime(db)
        spec = ResearchMemorySpec(
            job_id=job_id,
            scope=ResearchMemoryScope.job,
            memory_key="counter",
            value={"n": 1},
        )
        e1 = await rt.write(spec)
        e2 = await rt.write(ResearchMemorySpec(
            job_id=job_id,
            scope=ResearchMemoryScope.job,
            memory_key="counter",
            value={"n": 2},
        ))
        assert e1.memory_id == e2.memory_id
        read = await rt.read(job_id, ResearchMemoryScope.job, "counter")
        assert read is not None
        assert read.value == {"n": 2}

    async def test_read_missing_returns_none(self, db: AsyncSession) -> None:
        job_id = await self._make_job_id(db)
        rt = ResearchMemoryRuntime(db)
        result = await rt.read(job_id, ResearchMemoryScope.job, "missing_key")
        assert result is None

    async def test_ttl_expiry(self, db: AsyncSession) -> None:
        job_id = await self._make_job_id(db)
        rt = ResearchMemoryRuntime(db)
        spec = ResearchMemorySpec(
            job_id=job_id,
            scope=ResearchMemoryScope.task,
            memory_key="temp",
            value={"x": 1},
            ttl_seconds=1,
        )
        entry = await rt.write(spec)
        assert entry.expires_at is not None

        # Manually expire by adjusting expires_at in place
        from sqlalchemy import select  # noqa: PLC0415

        from models.research_memory import ResearchMemory  # noqa: PLC0415
        result = await db.execute(
            select(ResearchMemory).where(ResearchMemory.id == entry.memory_id)
        )
        row = result.scalar_one()
        row.expires_at = datetime.now(UTC) - timedelta(seconds=10)
        db.add(row)
        await db.flush()

        read = await rt.read(job_id, ResearchMemoryScope.task, "temp")
        assert read is None  # expired → None

    async def test_clear_job_memory(self, db: AsyncSession) -> None:
        job_id = await self._make_job_id(db)
        rt = ResearchMemoryRuntime(db)

        for i in range(3):
            await rt.write(ResearchMemorySpec(
                job_id=job_id,
                scope=ResearchMemoryScope.job,
                memory_key=f"key_{i}",
                value={"i": i},
            ))

        count = await rt.clear_job(job_id)
        assert count == 3

        entries = await rt.list_job(job_id)
        assert len(entries) == 0

    async def test_task_scoped_memory(self, db: AsyncSession) -> None:
        job_id = await self._make_job_id(db)
        task_id = uuid.uuid4()
        rt = ResearchMemoryRuntime(db)

        await rt.write(ResearchMemorySpec(
            job_id=job_id,
            scope=ResearchMemoryScope.task,
            memory_key="state",
            value={"progress": 0.5},
            task_id=task_id,
        ))

        read = await rt.read(job_id, ResearchMemoryScope.task, "state", task_id=task_id)
        assert read is not None
        assert read.task_id == task_id

        # Different task_id → miss
        other = await rt.read(job_id, ResearchMemoryScope.task, "state", task_id=uuid.uuid4())
        assert other is None


# ---------------------------------------------------------------------------
# ResearchPlanRuntime
# ---------------------------------------------------------------------------


class TestResearchPlanRuntime:
    async def _make_job_id(self, db: AsyncSession) -> uuid.UUID:
        rt = ResearchJobRuntime(db)
        r = await rt.create(_job_spec())
        r = await rt.start(r.job_id)
        return r.job_id

    def _plan_spec(self, **kwargs) -> ResearchPlanSpec:
        return ResearchPlanSpec(
            plan_key=kwargs.get("plan_key", f"plan-{uuid.uuid4()}"),
            goal=kwargs.get("goal", "Find information about X"),
            steps=kwargs.get("steps", ({"type": "search", "query": "X"},)),
            constraints=kwargs.get("constraints", {"max_sources": 10}),
            job_id=kwargs.get("job_id"),
        )

    async def test_create_plan(self, db: AsyncSession) -> None:
        rt = ResearchPlanRuntime(db)
        spec = self._plan_spec()
        plan = await rt.create(spec)

        assert plan.plan_key == spec.plan_key
        assert plan.status == ResearchPlanStatus.draft
        assert plan.revision == 0
        assert len(plan.steps) == 1

    async def test_create_idempotent(self, db: AsyncSession) -> None:
        rt = ResearchPlanRuntime(db)
        spec = self._plan_spec()
        p1 = await rt.create(spec)
        p2 = await rt.create(spec)
        assert p1.plan_id == p2.plan_id

    async def test_activate_plan(self, db: AsyncSession) -> None:
        rt = ResearchPlanRuntime(db)
        plan = await rt.create(self._plan_spec())
        plan = await rt.activate(plan.plan_id)
        assert plan.status == ResearchPlanStatus.active

    async def test_revise_plan(self, db: AsyncSession) -> None:
        rt = ResearchPlanRuntime(db)
        plan = await rt.create(self._plan_spec())
        plan = await rt.activate(plan.plan_id)

        revision = ResearchPlanRevision(
            plan_id=plan.plan_id,
            goal="Updated goal",
            steps=({"type": "search", "query": "X"}, {"type": "extract"}),
            constraints=None,
        )
        plan = await rt.revise(revision)

        assert plan.revision == 1
        assert plan.goal == "Updated goal"
        assert len(plan.steps) == 2
        assert plan.status == ResearchPlanStatus.revised

    async def test_complete_plan(self, db: AsyncSession) -> None:
        rt = ResearchPlanRuntime(db)
        plan = await rt.create(self._plan_spec())
        plan = await rt.complete(plan.plan_id)
        assert plan.status == ResearchPlanStatus.completed

    async def test_abandon_plan(self, db: AsyncSession) -> None:
        rt = ResearchPlanRuntime(db)
        plan = await rt.create(self._plan_spec())
        plan = await rt.activate(plan.plan_id)
        plan = await rt.abandon(plan.plan_id)
        assert plan.status == ResearchPlanStatus.abandoned

    async def test_cannot_revise_completed(self, db: AsyncSession) -> None:
        rt = ResearchPlanRuntime(db)
        plan = await rt.create(self._plan_spec())
        plan = await rt.complete(plan.plan_id)

        with pytest.raises(ResearchPlanError):
            await rt.revise(ResearchPlanRevision(
                plan_id=plan.plan_id,
                goal="New goal",
                steps=None,
                constraints=None,
            ))

    async def test_checkpoint_plan(self, db: AsyncSession) -> None:
        rt = ResearchPlanRuntime(db)
        plan = await rt.create(self._plan_spec())
        plan = await rt.activate(plan.plan_id)
        plan = await rt.checkpoint(plan.plan_id, {"cursor": "step_2"})

        assert plan.checkpoint_state == {"cursor": "step_2"}
        assert plan.status == ResearchPlanStatus.active  # unchanged


# ---------------------------------------------------------------------------
# ResearchSafetyRuntime
# ---------------------------------------------------------------------------


class TestResearchSafetyRuntime:
    async def _make_running_job(self, db: AsyncSession, token_budget: int = 1000) -> uuid.UUID:
        rt = ResearchJobRuntime(db)
        r = await rt.create(_job_spec(token_budget=token_budget))
        r = await rt.start(r.job_id)
        return r.job_id

    def _config(self, **kwargs) -> ResearchSafetyConfig:
        return ResearchSafetyConfig(
            max_tokens=kwargs.get("max_tokens", 1000),
            max_depth=kwargs.get("max_depth", 5),
            max_tasks=kwargs.get("max_tasks", 20),
            token_warning_threshold=kwargs.get("token_warning_threshold", 0.8),
            timeout_seconds=kwargs.get("timeout_seconds"),
        )

    async def test_check_budget_ok(self, db: AsyncSession) -> None:
        job_id = await self._make_running_job(db, token_budget=1000)
        rt = ResearchSafetyRuntime(db)
        state = await rt.check_budget(job_id, self._config(max_tokens=1000), tokens_to_add=100)

        assert state.over_budget is False
        assert state.tokens_used == 100

    async def test_check_budget_exceeded_raises(self, db: AsyncSession) -> None:
        job_id = await self._make_running_job(db, token_budget=100)
        rt = ResearchSafetyRuntime(db)

        with pytest.raises(ResearchBudgetExceededError):
            await rt.check_budget(job_id, self._config(max_tokens=100), tokens_to_add=200)

    async def test_check_budget_near_limit(self, db: AsyncSession) -> None:
        job_id = await self._make_running_job(db, token_budget=1000)
        rt = ResearchSafetyRuntime(db)
        state = await rt.check_budget(
            job_id, self._config(max_tokens=1000, token_warning_threshold=0.7),
            tokens_to_add=750,
        )
        assert state.near_limit is True
        assert state.over_budget is False

    async def test_check_depth_ok(self, db: AsyncSession) -> None:
        job_id = await self._make_running_job(db)
        rt = ResearchSafetyRuntime(db)
        await rt.check_depth(job_id, 3, self._config(max_depth=5))  # no raise

    async def test_check_depth_exceeded_raises(self, db: AsyncSession) -> None:
        job_id = await self._make_running_job(db)
        rt = ResearchSafetyRuntime(db)

        with pytest.raises(ResearchDepthExceededError):
            await rt.check_depth(job_id, 10, self._config(max_depth=5))

    async def test_record_dead_letter(self, db: AsyncSession) -> None:
        job_id = await self._make_running_job(db)
        rt = ResearchSafetyRuntime(db)
        task_id = uuid.uuid4()

        # Should not raise
        await rt.record_dead_letter(job_id, task_id, reason="orphaned task")

    async def test_check_timeout_no_timeout_config(self, db: AsyncSession) -> None:
        job_id = await self._make_running_job(db)
        rt = ResearchSafetyRuntime(db)
        config = self._config(timeout_seconds=None)
        timed_out = await rt.check_timeout(job_id, config)
        assert timed_out is False


# ---------------------------------------------------------------------------
# ResearchReplayRuntime (deterministic replay)
# ---------------------------------------------------------------------------


class TestResearchReplayRuntime:
    async def test_replay_frames_ordered(self, db: AsyncSession) -> None:
        """Frames must be in emission order — deterministic replay."""
        job_rt = ResearchJobRuntime(db)
        task_rt = ResearchTaskRuntime(db)

        r = await job_rt.create(_job_spec())
        r = await job_rt.start(r.job_id)
        job_id = r.job_id

        task = await task_rt.create(_task_spec(job_id))
        task = await task_rt.start(task.task_id)
        await task_rt.complete(task.task_id, output_payload={"ok": True})
        await job_rt.complete(job_id)

        replay = ResearchReplayRuntime(db)
        frames = await replay.get_frames(job_id)

        assert len(frames) >= 4  # job_created, job_started, task_*, job_completed
        for i, frame in enumerate(frames):
            assert frame.frame_index == i

    async def test_replay_event_types_present(self, db: AsyncSession) -> None:
        job_rt = ResearchJobRuntime(db)
        r = await job_rt.create(_job_spec())
        r = await job_rt.start(r.job_id)
        r = await job_rt.complete(r.job_id)

        replay = ResearchReplayRuntime(db)
        frames = await replay.get_frames(r.job_id)
        event_types = {f.event_type for f in frames}

        assert "job_created" in event_types
        assert "job_started" in event_types
        assert "job_completed" in event_types

    async def test_reconstruct_status_progression(self, db: AsyncSession) -> None:
        job_rt = ResearchJobRuntime(db)
        r = await job_rt.create(_job_spec())
        r = await job_rt.start(r.job_id)
        await job_rt.pause(r.job_id)
        await job_rt.resume(r.job_id)
        await job_rt.complete(r.job_id)

        replay = ResearchReplayRuntime(db)
        status_map = await replay.reconstruct_status(r.job_id)

        # All status events present
        event_names = set(status_map.values())
        assert "job_created" in event_names
        assert "job_started" in event_names
        assert "job_paused" in event_names
        assert "job_resumed" in event_names
        assert "job_completed" in event_names

    async def test_task_frames_scoped(self, db: AsyncSession) -> None:
        job_rt = ResearchJobRuntime(db)
        task_rt = ResearchTaskRuntime(db)

        r = await job_rt.create(_job_spec())
        r = await job_rt.start(r.job_id)

        t = await task_rt.create(_task_spec(r.job_id))
        t = await task_rt.start(t.task_id)
        await task_rt.complete(t.task_id, output_payload={})

        replay = ResearchReplayRuntime(db)
        task_frames = await replay.get_task_frames(t.task_id)
        event_types = {f.event_type for f in task_frames}

        assert "task_created" in event_types
        assert "task_started" in event_types
        assert "task_completed" in event_types

    async def test_empty_job_has_created_frame(self, db: AsyncSession) -> None:
        job_rt = ResearchJobRuntime(db)
        r = await job_rt.create(_job_spec())

        replay = ResearchReplayRuntime(db)
        frames = await replay.get_frames(r.job_id)
        assert len(frames) >= 1
        assert frames[0].event_type == "job_created"
        assert frames[0].frame_index == 0
