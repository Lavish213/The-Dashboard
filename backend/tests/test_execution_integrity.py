"""
Phase 7 — Execution Integrity Tests.

Covers:
- LeaseRuntime (acquire, renew, release, expire_stale, conflicts)
- WorkflowStepGraph (forward/backward validation, unknown steps)
- DeadLetterRuntime (mark, domain event, query)
- RetryCoordinator (schedule, get_due, exhaustion → dead-letter)
- StalledDetector (find_stalled, mark_stalled)
- OrphanedRecovery (find_orphaned, recover with/without checkpoint)
- ExecutionIntegrityRuntime (sweep, summary event)
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from events.replay import replay_channel
from models.enums import WorkflowStatus, WorkflowType
from workflows.checkpoint import CheckpointRuntime
from workflows.deadletter import EVT_DEAD_LETTER, DeadLetterRuntime
from workflows.graph import (
    StepTransitionError,
    get_valid_next_steps,
    is_valid_step,
    validate_step_advance,
)
from workflows.integrity import EVT_INTEGRITY_SWEEP, ExecutionIntegrityRuntime
from workflows.lease import (
    EVT_LEASE_ACQUIRED,
    EVT_LEASE_EXPIRED,
    EVT_LEASE_RELEASED,
    LeaseAcquireError,
    LeaseConflictError,
    LeaseRuntime,
)
from workflows.orphaned import (
    EVT_ORPHANED_CANCELLED,
    EVT_ORPHANED_DETECTED,
    EVT_ORPHANED_RECOVERED,
    OrphanedRecovery,
)
from workflows.persistence import WorkflowEventRepository
from workflows.retries import RetryExhaustedError, RetryPolicy
from workflows.retry_coordinator import (
    EVT_RETRY_ATTEMPTED,
    EVT_RETRY_EXHAUSTED,
    EVT_RETRY_SCHEDULED,
    RetryCoordinator,
)
from workflows.runtime import WorkflowRuntime
from workflows.stalled import EVT_STALLED, StalledDetector


async def _active(db: AsyncSession):
    return await WorkflowRuntime(db).start(WorkflowType.outreach)


async def _failed(db: AsyncSession):
    rt = WorkflowRuntime(db)
    wf = await rt.start(WorkflowType.outreach)
    await rt.fail(wf.id, reason="test_failure")
    return wf


# ---------------------------------------------------------------------------
# LeaseRuntime
# ---------------------------------------------------------------------------


class TestLeaseRuntime:
    async def test_acquire_creates_lease(self, db: AsyncSession) -> None:
        wf = await _active(db)
        result = await LeaseRuntime(db).acquire(wf.id, holder="worker-1")
        assert result.workflow_id == wf.id
        assert result.holder == "worker-1"
        assert result.expires_at > datetime.now(UTC)

    async def test_acquire_emits_domain_event(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await LeaseRuntime(db).acquire(wf.id, holder="worker-1")
        stored, _ = await replay_channel(db, "workflows")
        assert any(e.event_type == EVT_LEASE_ACQUIRED for e in stored)

    async def test_acquire_blocks_concurrent_holder(self, db: AsyncSession) -> None:
        wf = await _active(db)
        lease_rt = LeaseRuntime(db)
        await lease_rt.acquire(wf.id, holder="worker-1")
        with pytest.raises(LeaseAcquireError):
            await lease_rt.acquire(wf.id, holder="worker-2")

    async def test_acquire_same_holder_refreshes(self, db: AsyncSession) -> None:
        wf = await _active(db)
        lease_rt = LeaseRuntime(db)
        await lease_rt.acquire(wf.id, holder="worker-1")
        r2 = await lease_rt.acquire(wf.id, holder="worker-1")
        assert r2.holder == "worker-1"

    async def test_acquire_after_expiry_succeeds(self, db: AsyncSession) -> None:
        wf = await _active(db)
        lease_rt = LeaseRuntime(db)
        await lease_rt.acquire(wf.id, holder="worker-1", ttl_seconds=1)
        future = datetime.now(UTC) + timedelta(seconds=10)
        await lease_rt.expire_stale(now=future)
        r2 = await lease_rt.acquire(wf.id, holder="worker-2")
        assert r2.holder == "worker-2"

    async def test_renew_extends_expiry(self, db: AsyncSession) -> None:
        wf = await _active(db)
        lease_rt = LeaseRuntime(db)
        r1 = await lease_rt.acquire(wf.id, holder="worker-1")
        r2 = await lease_rt.renew(wf.id, r1.lease_id, ttl_seconds=600)
        assert r2.expires_at > r1.expires_at
        assert r2.was_renewed is True

    async def test_renew_wrong_lease_id_raises(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await LeaseRuntime(db).acquire(wf.id, holder="worker-1")
        with pytest.raises(LeaseConflictError):
            await LeaseRuntime(db).renew(wf.id, uuid4())

    async def test_release_clears_active_lease(self, db: AsyncSession) -> None:
        wf = await _active(db)
        lease_rt = LeaseRuntime(db)
        r = await lease_rt.acquire(wf.id, holder="worker-1")
        await lease_rt.release(wf.id, r.lease_id)
        assert await lease_rt.get_active(wf.id) is None

    async def test_release_emits_domain_event(self, db: AsyncSession) -> None:
        wf = await _active(db)
        lease_rt = LeaseRuntime(db)
        r = await lease_rt.acquire(wf.id, holder="worker-1")
        await lease_rt.release(wf.id, r.lease_id)
        stored, _ = await replay_channel(db, "workflows")
        assert any(e.event_type == EVT_LEASE_RELEASED for e in stored)

    async def test_release_idempotent(self, db: AsyncSession) -> None:
        wf = await _active(db)
        lease_rt = LeaseRuntime(db)
        r = await lease_rt.acquire(wf.id, holder="worker-1")
        await lease_rt.release(wf.id, r.lease_id)
        await lease_rt.release(wf.id, r.lease_id)  # no raise

    async def test_release_wrong_lease_id_raises(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await LeaseRuntime(db).acquire(wf.id, holder="worker-1")
        with pytest.raises(LeaseConflictError):
            await LeaseRuntime(db).release(wf.id, uuid4())

    async def test_expire_stale_returns_workflow_ids(self, db: AsyncSession) -> None:
        wf = await _active(db)
        lease_rt = LeaseRuntime(db)
        await lease_rt.acquire(wf.id, holder="worker-1", ttl_seconds=1)
        future = datetime.now(UTC) + timedelta(seconds=10)
        expired = await lease_rt.expire_stale(now=future)
        assert wf.id in expired

    async def test_expire_stale_emits_domain_event(self, db: AsyncSession) -> None:
        wf = await _active(db)
        lease_rt = LeaseRuntime(db)
        await lease_rt.acquire(wf.id, holder="worker-1", ttl_seconds=1)
        future = datetime.now(UTC) + timedelta(seconds=10)
        await lease_rt.expire_stale(now=future)
        stored, _ = await replay_channel(db, "workflows")
        assert any(e.event_type == EVT_LEASE_EXPIRED for e in stored)

    async def test_get_active_returns_none_without_lease(self, db: AsyncSession) -> None:
        wf = await _active(db)
        assert await LeaseRuntime(db).get_active(wf.id) is None

    async def test_fresh_lease_not_expired(self, db: AsyncSession) -> None:
        wf = await _active(db)
        lease_rt = LeaseRuntime(db)
        await lease_rt.acquire(wf.id, holder="worker-1", ttl_seconds=300)
        # Expire sweep at now — fresh lease should not be expired
        expired = await lease_rt.expire_stale(now=datetime.now(UTC))
        assert wf.id not in expired


# ---------------------------------------------------------------------------
# WorkflowStepGraph
# ---------------------------------------------------------------------------


class TestWorkflowStepGraph:
    def test_valid_forward_step(self) -> None:
        validate_step_advance(WorkflowType.outreach, "contacted", "qualified")

    def test_valid_skip_forward(self) -> None:
        validate_step_advance(WorkflowType.outreach, "contacted", "offered")

    def test_backward_step_raises(self) -> None:
        with pytest.raises(StepTransitionError):
            validate_step_advance(WorkflowType.outreach, "qualified", "contacted")

    def test_same_step_raises(self) -> None:
        with pytest.raises(StepTransitionError):
            validate_step_advance(WorkflowType.outreach, "contacted", "contacted")

    def test_unknown_from_step_allowed(self) -> None:
        validate_step_advance(WorkflowType.outreach, "custom_step", "qualified")

    def test_unknown_to_step_allowed(self) -> None:
        validate_step_advance(WorkflowType.outreach, "contacted", "custom_step")

    def test_none_current_step_allowed(self) -> None:
        validate_step_advance(WorkflowType.outreach, None, "contacted")

    def test_is_valid_step_known(self) -> None:
        assert is_valid_step(WorkflowType.outreach, "contacted") is True

    def test_is_valid_step_unknown(self) -> None:
        assert is_valid_step(WorkflowType.outreach, "custom_step") is False

    def test_get_valid_next_steps_first(self) -> None:
        steps = get_valid_next_steps(WorkflowType.outreach, None)
        assert "contacted" in steps

    def test_get_valid_next_steps_middle(self) -> None:
        steps = get_valid_next_steps(WorkflowType.outreach, "contacted")
        assert "qualified" in steps
        assert "contacted" not in steps

    def test_terminal_step_no_successors(self) -> None:
        assert get_valid_next_steps(WorkflowType.outreach, "closed") == []

    def test_all_workflow_types_have_graphs(self) -> None:
        from workflows.graph import STEP_GRAPH
        for wt in WorkflowType:
            assert wt in STEP_GRAPH, f"{wt} missing from STEP_GRAPH"


# ---------------------------------------------------------------------------
# DeadLetterRuntime
# ---------------------------------------------------------------------------


class TestDeadLetterRuntime:
    async def test_mark_returns_record(self, db: AsyncSession) -> None:
        wf = await _failed(db)
        record = await DeadLetterRuntime(db).mark(
            wf.id, reason="timeout", retry_count=3, last_error="conn refused"
        )
        assert record.reason == "timeout"
        assert record.retry_count == 3

    async def test_mark_emits_domain_event(self, db: AsyncSession) -> None:
        wf = await _failed(db)
        await DeadLetterRuntime(db).mark(wf.id, reason="timeout")
        stored, _ = await replay_channel(db, "workflows")
        assert any(e.event_type == EVT_DEAD_LETTER for e in stored)

    async def test_mark_records_workflow_event(self, db: AsyncSession) -> None:
        wf = await _failed(db)
        await DeadLetterRuntime(db).mark(wf.id, reason="timeout", retry_count=2)
        events = await WorkflowEventRepository(db).get_by_workflow(wf.id)
        assert any(e.event_type == EVT_DEAD_LETTER for e in events)

    async def test_get_dead_letters_returns_records(self, db: AsyncSession) -> None:
        wf = await _failed(db)
        await DeadLetterRuntime(db).mark(wf.id, reason="test_dl")
        records = await DeadLetterRuntime(db).get_dead_letters()
        assert any(r.workflow_id == wf.id for r in records)


# ---------------------------------------------------------------------------
# RetryCoordinator
# ---------------------------------------------------------------------------


class TestRetryCoordinator:
    async def test_schedule_returns_scheduled_retry(self, db: AsyncSession) -> None:
        wf = await _failed(db)
        result = await RetryCoordinator(db).schedule(wf.id, error="network error")
        assert result.workflow_id == wf.id
        assert result.attempt == 1
        assert result.next_retry_at > datetime.now(UTC)

    async def test_schedule_emits_domain_event(self, db: AsyncSession) -> None:
        wf = await _failed(db)
        await RetryCoordinator(db).schedule(wf.id, error="err")
        stored, _ = await replay_channel(db, "workflows")
        assert any(e.event_type == EVT_RETRY_SCHEDULED for e in stored)

    async def test_schedule_records_workflow_event(self, db: AsyncSession) -> None:
        wf = await _failed(db)
        await RetryCoordinator(db).schedule(wf.id, error="err")
        events = await WorkflowEventRepository(db).get_by_workflow(wf.id)
        assert any(e.event_type == EVT_RETRY_SCHEDULED for e in events)

    async def test_schedule_increments_attempt(self, db: AsyncSession) -> None:
        wf = await _failed(db)
        coord = RetryCoordinator(db)
        policy = RetryPolicy(max_retries=3)
        r1 = await coord.schedule(wf.id, error="err1", policy=policy)
        r2 = await coord.schedule(wf.id, error="err2", policy=policy)
        assert r2.attempt == r1.attempt + 1

    async def test_schedule_exhaustion_raises_and_dead_letters(
        self, db: AsyncSession
    ) -> None:
        wf = await _failed(db)
        coord = RetryCoordinator(db)
        policy = RetryPolicy(max_retries=1)
        await coord.schedule(wf.id, error="err1", policy=policy)
        with pytest.raises(RetryExhaustedError):
            await coord.schedule(wf.id, error="err2", policy=policy)
        events = await WorkflowEventRepository(db).get_by_workflow(wf.id)
        assert any(e.event_type == EVT_RETRY_EXHAUSTED for e in events)
        assert any(e.event_type == EVT_DEAD_LETTER for e in events)

    async def test_get_due_returns_due_retries(self, db: AsyncSession) -> None:
        wf = await _failed(db)
        await RetryCoordinator(db).schedule(wf.id, error="err")
        future = datetime.now(UTC) + timedelta(hours=2)
        due = await RetryCoordinator(db).get_due(now=future)
        assert any(r.workflow_id == wf.id for r in due)

    async def test_get_due_excludes_not_yet_due(self, db: AsyncSession) -> None:
        wf = await _failed(db)
        await RetryCoordinator(db).schedule(wf.id, error="err")
        due = await RetryCoordinator(db).get_due(now=datetime.now(UTC))
        assert not any(r.workflow_id == wf.id for r in due)

    async def test_mark_attempted_records_event(self, db: AsyncSession) -> None:
        wf = await _failed(db)
        coord = RetryCoordinator(db)
        await coord.schedule(wf.id, error="err")
        await coord.mark_attempted(wf.id)
        events = await WorkflowEventRepository(db).get_by_workflow(wf.id)
        assert any(e.event_type == EVT_RETRY_ATTEMPTED for e in events)


# ---------------------------------------------------------------------------
# StalledDetector
# ---------------------------------------------------------------------------


class TestStalledDetector:
    async def test_find_stalled_returns_idle_workflows(self, db: AsyncSession) -> None:
        wf = await _active(db)
        future = datetime.now(UTC) + timedelta(hours=3)
        stalled = await StalledDetector(db).find_stalled(max_idle_seconds=60, now=future)
        assert any(s.workflow_id == wf.id for s in stalled)

    async def test_find_stalled_excludes_fresh_workflows(self, db: AsyncSession) -> None:
        wf = await _active(db)
        stalled = await StalledDetector(db).find_stalled(max_idle_seconds=3600)
        assert not any(s.workflow_id == wf.id for s in stalled)

    async def test_find_stalled_excludes_terminal(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await WorkflowRuntime(db).complete(wf.id)
        future = datetime.now(UTC) + timedelta(hours=3)
        stalled = await StalledDetector(db).find_stalled(max_idle_seconds=60, now=future)
        assert not any(s.workflow_id == wf.id for s in stalled)

    async def test_mark_stalled_emits_domain_event(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await StalledDetector(db).mark_stalled(wf.id, stalled_for_seconds=3700.0)
        stored, _ = await replay_channel(db, "workflows")
        assert any(e.event_type == EVT_STALLED for e in stored)

    async def test_stalled_result_has_correct_fields(self, db: AsyncSession) -> None:
        wf = await _active(db)
        future = datetime.now(UTC) + timedelta(hours=3)
        stalled = await StalledDetector(db).find_stalled(max_idle_seconds=60, now=future)
        match = next(s for s in stalled if s.workflow_id == wf.id)
        assert match.current_status == WorkflowStatus.active
        assert match.stalled_for_seconds > 0


# ---------------------------------------------------------------------------
# OrphanedRecovery
# ---------------------------------------------------------------------------


class TestOrphanedRecovery:
    async def test_find_orphaned_excludes_no_lease_workflows(
        self, db: AsyncSession
    ) -> None:
        # Workflows without a lease are NOT orphaned (never executed)
        wf = await _active(db)
        orphaned = await OrphanedRecovery(db).find_orphaned()
        assert not any(o.workflow_id == wf.id for o in orphaned)

    async def test_find_orphaned_excludes_active_lease(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await LeaseRuntime(db).acquire(wf.id, holder="worker-1")
        orphaned = await OrphanedRecovery(db).find_orphaned()
        assert not any(o.workflow_id == wf.id for o in orphaned)

    async def test_find_orphaned_includes_expired_lease(self, db: AsyncSession) -> None:
        wf = await _active(db)
        lease_rt = LeaseRuntime(db)
        await lease_rt.acquire(wf.id, holder="worker-1", ttl_seconds=1)
        future = datetime.now(UTC) + timedelta(seconds=10)
        await lease_rt.expire_stale(now=future)
        orphaned = await OrphanedRecovery(db).find_orphaned()
        assert any(o.workflow_id == wf.id for o in orphaned)

    async def test_recover_with_checkpoint_restores(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await CheckpointRuntime(db).set(
            wf.id, step="contacted", status=WorkflowStatus.active
        )
        result = await OrphanedRecovery(db).recover(wf.id)
        assert result is not None
        assert result.restored_from_step == "contacted"
        assert result.workflow.workflow_status == WorkflowStatus.active

    async def test_recover_without_checkpoint_cancels(self, db: AsyncSession) -> None:
        wf = await _active(db)
        result = await OrphanedRecovery(db).recover(wf.id)
        assert result is None
        from workflows.persistence import WorkflowRepository
        fetched = await WorkflowRepository(db).get_by_id(wf.id)
        assert fetched is not None
        assert fetched.workflow_status == WorkflowStatus.cancelled

    async def test_recover_emits_detected_event(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await CheckpointRuntime(db).set(
            wf.id, step="contacted", status=WorkflowStatus.active
        )
        await OrphanedRecovery(db).recover(wf.id)
        stored, _ = await replay_channel(db, "workflows")
        assert any(e.event_type == EVT_ORPHANED_DETECTED for e in stored)

    async def test_recover_with_checkpoint_emits_recovered(
        self, db: AsyncSession
    ) -> None:
        wf = await _active(db)
        await CheckpointRuntime(db).set(
            wf.id, step="step_x", status=WorkflowStatus.active
        )
        await OrphanedRecovery(db).recover(wf.id)
        stored, _ = await replay_channel(db, "workflows")
        assert any(e.event_type == EVT_ORPHANED_RECOVERED for e in stored)

    async def test_recover_without_checkpoint_emits_cancelled(
        self, db: AsyncSession
    ) -> None:
        wf = await _active(db)
        await OrphanedRecovery(db).recover(wf.id)
        stored, _ = await replay_channel(db, "workflows")
        assert any(e.event_type == EVT_ORPHANED_CANCELLED for e in stored)


# ---------------------------------------------------------------------------
# ExecutionIntegrityRuntime
# ---------------------------------------------------------------------------


class TestExecutionIntegrityRuntime:
    async def test_sweep_returns_result(self, db: AsyncSession) -> None:
        result = await ExecutionIntegrityRuntime(db).run_integrity_sweep()
        assert result.swept_at is not None

    async def test_sweep_emits_summary_event(self, db: AsyncSession) -> None:
        await ExecutionIntegrityRuntime(db).run_integrity_sweep()
        stored, _ = await replay_channel(db, "workflows")
        assert any(e.event_type == EVT_INTEGRITY_SWEEP for e in stored)

    async def test_sweep_detects_stalled_workflows(self, db: AsyncSession) -> None:
        wf = await _active(db)
        future = datetime.now(UTC) + timedelta(hours=3)
        stalled = await StalledDetector(db).find_stalled(max_idle_seconds=60, now=future)
        assert any(s.workflow_id == wf.id for s in stalled)

    async def test_sweep_recovers_orphaned_with_checkpoint(
        self, db: AsyncSession
    ) -> None:
        wf = await _active(db)
        await CheckpointRuntime(db).set(
            wf.id, step="contacted", status=WorkflowStatus.active
        )
        lease_rt = LeaseRuntime(db)
        await lease_rt.acquire(wf.id, holder="worker-crashed", ttl_seconds=1)
        future = datetime.now(UTC) + timedelta(seconds=10)
        await lease_rt.expire_stale(now=future)

        result = await ExecutionIntegrityRuntime(db).run_integrity_sweep()
        assert result.orphaned_detected >= 1
        assert result.orphaned_recovered >= 1

    async def test_sweep_no_errors_on_clean_state(self, db: AsyncSession) -> None:
        result = await ExecutionIntegrityRuntime(db).run_integrity_sweep()
        assert result.errors == []
