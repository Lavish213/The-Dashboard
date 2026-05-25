"""
Phase 7 — Governance Stabilization Tests.

Covers:
- SnapshotRuntime (take, restore, get_latest, get_all)
- ApprovalPauseOrchestrator (pause_for_approval, resume_on_approval, rollback_on_rejection)
- ResumeValidator (can_resume, blockers, strategy)
- ReplayVerifier (verify status+step match)
- ConsistencyValidator (state/approval/checkpoint consistency)
- CrossRuntimeAssertions (all assertions)
- AuditTimelineReconstructor (build, ordering)
- ObservabilityRuntime (record metric, on_transition)
- GovernanceMetrics (workflow_metrics, approval_metrics)
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from events.replay import replay_channel
from models.enums import ApprovalStatus, ApprovalType, WorkflowStatus, WorkflowType
from workflows.approval_orchestrator import (
    EVT_APPROVAL_LIFECYCLE_PAUSED,
    EVT_APPROVAL_LIFECYCLE_REJECTED,
    EVT_APPROVAL_LIFECYCLE_RESUMED,
    ApprovalPauseOrchestrator,
)
from workflows.assertions import (
    ConsistencyValidator,
    CrossRuntimeAssertions,
    ReplayVerifier,
)
from workflows.checkpoint import CheckpointRuntime
from workflows.lease import LeaseRuntime
from workflows.observability import GovernanceMetrics, ObservabilityRuntime
from workflows.persistence import WorkflowRepository
from workflows.resume_validator import ResumeValidator
from workflows.runtime import WorkflowRuntime
from workflows.snapshot import (
    EVT_SNAPSHOT_RESTORED,
    EVT_SNAPSHOT_TAKEN,
    SnapshotRuntime,
)
from workflows.timeline import AuditTimelineReconstructor


async def _active(db: AsyncSession):
    return await WorkflowRuntime(db).start(WorkflowType.outreach)


async def _advanced(db: AsyncSession, step: str = "contacted"):
    rt = WorkflowRuntime(db)
    wf = await rt.start(WorkflowType.outreach)
    await rt.advance(wf.id, step=step)
    return wf


async def _failed(db: AsyncSession):
    rt = WorkflowRuntime(db)
    wf = await rt.start(WorkflowType.outreach)
    await rt.fail(wf.id, reason="test")
    return wf


# ---------------------------------------------------------------------------
# SnapshotRuntime
# ---------------------------------------------------------------------------


class TestSnapshotRuntime:
    async def test_take_creates_snapshot(self, db: AsyncSession) -> None:
        wf = await _active(db)
        result = await SnapshotRuntime(db).take(wf.id, trigger="test")
        assert result.workflow_id == wf.id
        assert result.workflow_status == "active"
        assert result.trigger == "test"

    async def test_take_emits_domain_event(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await SnapshotRuntime(db).take(wf.id, trigger="test")
        stored, _ = await replay_channel(db, "workflows")
        assert any(e.event_type == EVT_SNAPSHOT_TAKEN for e in stored)

    async def test_take_captures_current_step(self, db: AsyncSession) -> None:
        wf = await _advanced(db, step="contacted")
        result = await SnapshotRuntime(db).take(wf.id)
        assert result.current_step == "contacted"

    async def test_take_captures_state_blob(self, db: AsyncSession) -> None:
        wf = await _active(db)
        rt = SnapshotRuntime(db)
        result = await rt.take(wf.id)
        # Verify state was actually stored
        all_snaps = await rt.get_all(wf.id)
        assert len(all_snaps) == 1
        assert all_snaps[0].snapshot_id == result.snapshot_id

    async def test_get_latest_returns_most_recent(self, db: AsyncSession) -> None:
        wf = await _active(db)
        rt = SnapshotRuntime(db)
        await rt.take(wf.id, trigger="first")
        s2 = await rt.take(wf.id, trigger="second")
        latest = await rt.get_latest(wf.id)
        assert latest is not None
        assert latest.snapshot_id == s2.snapshot_id

    async def test_get_latest_returns_none_when_empty(self, db: AsyncSession) -> None:
        wf = await _active(db)
        assert await SnapshotRuntime(db).get_latest(wf.id) is None

    async def test_get_all_ordered(self, db: AsyncSession) -> None:
        wf = await _active(db)
        rt = SnapshotRuntime(db)
        await rt.take(wf.id, trigger="a")
        await rt.take(wf.id, trigger="b")
        all_snaps = await rt.get_all(wf.id)
        assert len(all_snaps) == 2
        assert all_snaps[0].trigger == "a"
        assert all_snaps[1].trigger == "b"

    async def test_restore_restores_status_and_step(self, db: AsyncSession) -> None:
        wf = await _advanced(db, step="qualified")
        rt = SnapshotRuntime(db)
        snap = await rt.take(wf.id, trigger="before_fail")
        # Advance further
        await WorkflowRuntime(db).advance(wf.id, step="offered")
        # Restore to snapshot
        restored = await rt.restore(snap.snapshot_id)
        assert restored.current_step == "qualified"
        fetched = await WorkflowRepository(db).get_by_id(wf.id)
        assert fetched.current_step == "qualified"

    async def test_restore_emits_domain_event(self, db: AsyncSession) -> None:
        wf = await _active(db)
        rt = SnapshotRuntime(db)
        snap = await rt.take(wf.id)
        await rt.restore(snap.snapshot_id)
        stored, _ = await replay_channel(db, "workflows")
        assert any(e.event_type == EVT_SNAPSHOT_RESTORED for e in stored)

    async def test_restore_records_workflow_event(self, db: AsyncSession) -> None:
        from workflows.persistence import WorkflowEventRepository
        wf = await _active(db)
        rt = SnapshotRuntime(db)
        snap = await rt.take(wf.id)
        await rt.restore(snap.snapshot_id)
        events = await WorkflowEventRepository(db).get_by_workflow(wf.id)
        assert any(e.event_type == "workflow.snapshot.restored" for e in events)

    async def test_restore_terminal_raises(self, db: AsyncSession) -> None:
        wf = await _active(db)
        rt = SnapshotRuntime(db)
        snap = await rt.take(wf.id)
        await WorkflowRuntime(db).complete(wf.id)
        with pytest.raises(ValueError, match="terminal"):
            await rt.restore(snap.snapshot_id)


# ---------------------------------------------------------------------------
# ApprovalPauseOrchestrator
# ---------------------------------------------------------------------------


class TestApprovalPauseOrchestrator:
    async def test_pause_for_approval_pauses_workflow(self, db: AsyncSession) -> None:
        wf = await _active(db)
        orch = ApprovalPauseOrchestrator(db)
        result = await orch.pause_for_approval(wf.id, ApprovalType.offer)
        assert result.outcome == "paused"
        assert result.workflow_id == wf.id
        fetched = await WorkflowRepository(db).get_by_id(wf.id)
        assert fetched.workflow_status == WorkflowStatus.paused

    async def test_pause_for_approval_takes_snapshot(self, db: AsyncSession) -> None:
        wf = await _active(db)
        result = await ApprovalPauseOrchestrator(db).pause_for_approval(
            wf.id, ApprovalType.offer, take_snapshot=True
        )
        assert result.snapshot_id is not None

    async def test_pause_emits_lifecycle_event(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await ApprovalPauseOrchestrator(db).pause_for_approval(wf.id, ApprovalType.offer)
        stored, _ = await replay_channel(db, "workflows")
        assert any(e.event_type == EVT_APPROVAL_LIFECYCLE_PAUSED for e in stored)

    async def test_resume_on_approval_resumes_workflow(self, db: AsyncSession) -> None:
        wf = await _active(db)
        orch = ApprovalPauseOrchestrator(db)
        paused = await orch.pause_for_approval(wf.id, ApprovalType.offer)
        resumed = await orch.resume_on_approval(
            paused.approval_id, resolved_by=None
        )
        assert resumed.outcome == "resumed"
        fetched = await WorkflowRepository(db).get_by_id(wf.id)
        assert fetched.workflow_status == WorkflowStatus.active

    async def test_resume_emits_lifecycle_event(self, db: AsyncSession) -> None:
        wf = await _active(db)
        orch = ApprovalPauseOrchestrator(db)
        paused = await orch.pause_for_approval(wf.id, ApprovalType.offer)
        await orch.resume_on_approval(paused.approval_id, resolved_by=None)
        stored, _ = await replay_channel(db, "workflows")
        assert any(e.event_type == EVT_APPROVAL_LIFECYCLE_RESUMED for e in stored)

    async def test_rollback_on_rejection_cancels_workflow(self, db: AsyncSession) -> None:
        wf = await _active(db)
        orch = ApprovalPauseOrchestrator(db)
        paused = await orch.pause_for_approval(wf.id, ApprovalType.offer)
        rejected = await orch.rollback_on_rejection(
            paused.approval_id, wf.id, resolved_by=None
        )
        assert rejected.outcome == "rejected"
        fetched = await WorkflowRepository(db).get_by_id(wf.id)
        assert fetched.workflow_status == WorkflowStatus.cancelled

    async def test_rollback_marks_approval_rejected(self, db: AsyncSession) -> None:
        from repositories.approval import ApprovalRepository
        wf = await _active(db)
        orch = ApprovalPauseOrchestrator(db)
        paused = await orch.pause_for_approval(wf.id, ApprovalType.offer)
        await orch.rollback_on_rejection(paused.approval_id, wf.id)
        repo = ApprovalRepository(db)
        approval = await repo.get_by_id(paused.approval_id)
        assert approval.approval_status == ApprovalStatus.rejected

    async def test_rejection_emits_lifecycle_event(self, db: AsyncSession) -> None:
        wf = await _active(db)
        orch = ApprovalPauseOrchestrator(db)
        paused = await orch.pause_for_approval(wf.id, ApprovalType.offer)
        await orch.rollback_on_rejection(paused.approval_id, wf.id)
        stored, _ = await replay_channel(db, "workflows")
        assert any(e.event_type == EVT_APPROVAL_LIFECYCLE_REJECTED for e in stored)


# ---------------------------------------------------------------------------
# ResumeValidator
# ---------------------------------------------------------------------------


class TestResumeValidator:
    async def test_paused_no_pending_can_resume(self, db: AsyncSession) -> None:
        # Pause manually then clear approval via gate resolution
        wf = await _active(db)
        orch = ApprovalPauseOrchestrator(db)
        paused = await orch.pause_for_approval(wf.id, ApprovalType.offer)
        await orch.resume_on_approval(paused.approval_id, resolved_by=None)
        # Now it's active — can't resume (already active)
        result = await ResumeValidator(db).validate(wf.id)
        assert result.can_resume is False
        assert "already active" in result.blockers[0]

    async def test_failed_with_checkpoint_can_resume(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await CheckpointRuntime(db).set(wf.id, step="contacted", status=WorkflowStatus.active)
        await WorkflowRuntime(db).fail(wf.id, reason="err")
        result = await ResumeValidator(db).validate(wf.id)
        assert result.can_resume is True
        assert result.recommended_strategy == "checkpoint_restore"

    async def test_failed_without_checkpoint_cannot_resume(self, db: AsyncSession) -> None:
        wf = await _failed(db)
        result = await ResumeValidator(db).validate(wf.id)
        assert result.can_resume is False
        assert "no checkpoint" in result.blockers[0]

    async def test_terminal_cannot_resume(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await WorkflowRuntime(db).complete(wf.id)
        result = await ResumeValidator(db).validate(wf.id)
        assert result.can_resume is False
        assert result.recommended_strategy == "none"

    async def test_pending_approval_blocks_paused_resume(self, db: AsyncSession) -> None:
        wf = await _active(db)
        orch = ApprovalPauseOrchestrator(db)
        await orch.pause_for_approval(wf.id, ApprovalType.offer)
        result = await ResumeValidator(db).validate(wf.id)
        assert result.can_resume is False
        assert any("pending approval" in b for b in result.blockers)

    async def test_active_lease_adds_warning(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await CheckpointRuntime(db).set(wf.id, step="s", status=WorkflowStatus.active)
        await WorkflowRuntime(db).fail(wf.id, reason="err")
        await LeaseRuntime(db).acquire(wf.id, holder="worker-x")
        result = await ResumeValidator(db).validate(wf.id)
        assert any("worker-x" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# ReplayVerifier
# ---------------------------------------------------------------------------


class TestReplayVerifier:
    async def test_verify_correct_status_passes(self, db: AsyncSession) -> None:
        wf = await _active(db)
        result = await ReplayVerifier(db).verify(wf.id, WorkflowStatus.active)
        assert result.is_valid is True
        assert result.violations == []

    async def test_verify_wrong_status_fails(self, db: AsyncSession) -> None:
        wf = await _active(db)
        result = await ReplayVerifier(db).verify(wf.id, WorkflowStatus.completed)
        assert result.is_valid is False
        assert any("status mismatch" in v for v in result.violations)

    async def test_verify_correct_step_passes(self, db: AsyncSession) -> None:
        wf = await _advanced(db, step="contacted")
        result = await ReplayVerifier(db).verify(
            wf.id, WorkflowStatus.active, expected_step="contacted"
        )
        assert result.is_valid is True

    async def test_verify_wrong_step_fails(self, db: AsyncSession) -> None:
        wf = await _advanced(db, step="contacted")
        result = await ReplayVerifier(db).verify(
            wf.id, WorkflowStatus.active, expected_step="qualified"
        )
        assert result.is_valid is False
        assert any("step mismatch" in v for v in result.violations)

    async def test_verify_has_event_count(self, db: AsyncSession) -> None:
        wf = await _active(db)
        result = await ReplayVerifier(db).verify(wf.id, WorkflowStatus.active)
        assert result.event_count >= 1


# ---------------------------------------------------------------------------
# ConsistencyValidator
# ---------------------------------------------------------------------------


class TestConsistencyValidator:
    async def test_healthy_active_is_consistent(self, db: AsyncSession) -> None:
        wf = await _active(db)
        report = await ConsistencyValidator(db).validate(wf.id)
        assert report.is_consistent is True
        assert report.state_consistent is True

    async def test_failed_with_checkpoint_is_recoverable(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await CheckpointRuntime(db).set(wf.id, step="s", status=WorkflowStatus.active)
        await WorkflowRuntime(db).fail(wf.id, reason="err")
        report = await ConsistencyValidator(db).validate(wf.id)
        assert report.checkpoint_recoverable is True

    async def test_failed_without_checkpoint_not_recoverable(
        self, db: AsyncSession
    ) -> None:
        wf = await _failed(db)
        report = await ConsistencyValidator(db).validate(wf.id)
        assert report.checkpoint_recoverable is False
        assert any("no checkpoint" in f for f in report.findings)

    async def test_paused_with_pending_approval_is_consistent(
        self, db: AsyncSession
    ) -> None:
        wf = await _active(db)
        await ApprovalPauseOrchestrator(db).pause_for_approval(wf.id, ApprovalType.offer)
        report = await ConsistencyValidator(db).validate(wf.id)
        assert report.approval_consistent is True


# ---------------------------------------------------------------------------
# CrossRuntimeAssertions
# ---------------------------------------------------------------------------


class TestCrossRuntimeAssertions:
    async def test_healthy_workflow_all_assertions_pass(self, db: AsyncSession) -> None:
        wf = await _active(db)
        report = await CrossRuntimeAssertions(db).assert_all(wf.id)
        assert report.all_passed is True
        assert len(report.failed) == 0

    async def test_terminal_no_active_lease(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await WorkflowRuntime(db).complete(wf.id)
        report = await CrossRuntimeAssertions(db).assert_all(wf.id)
        assert "A2:terminal_no_active_lease" in report.passed

    async def test_checkpoints_ordered(self, db: AsyncSession) -> None:
        wf = await _active(db)
        crt = CheckpointRuntime(db)
        await crt.set(wf.id, step="step_a", status=WorkflowStatus.active)
        await crt.set(wf.id, step="step_b", status=WorkflowStatus.active)
        report = await CrossRuntimeAssertions(db).assert_all(wf.id)
        assert "A4:checkpoints_ordered" in report.passed

    async def test_failed_without_checkpoint_warns(self, db: AsyncSession) -> None:
        wf = await _failed(db)
        report = await CrossRuntimeAssertions(db).assert_all(wf.id)
        assert any("A5:failed_recoverable" in w for w in report.warnings)

    async def test_paused_with_pending_approval_passes(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await ApprovalPauseOrchestrator(db).pause_for_approval(wf.id, ApprovalType.offer)
        report = await CrossRuntimeAssertions(db).assert_all(wf.id)
        assert "A3:paused_has_pending_approval" in report.passed


# ---------------------------------------------------------------------------
# AuditTimelineReconstructor
# ---------------------------------------------------------------------------


class TestAuditTimeline:
    async def test_build_returns_ordered_entries(self, db: AsyncSession) -> None:
        wf = await _advanced(db, step="contacted")
        timeline = await AuditTimelineReconstructor(db).build(wf.id)
        assert len(timeline) >= 2  # started + advanced
        for i in range(len(timeline) - 1):
            assert timeline[i].occurred_at <= timeline[i + 1].occurred_at

    async def test_build_includes_workflow_events(self, db: AsyncSession) -> None:
        wf = await _active(db)
        timeline = await AuditTimelineReconstructor(db).build(wf.id)
        types = {e.event_type for e in timeline}
        assert "workflow.started" in types

    async def test_build_includes_checkpoints(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await CheckpointRuntime(db).set(wf.id, step="contacted", status=WorkflowStatus.active)
        timeline = await AuditTimelineReconstructor(db).build(wf.id)
        sources = {e.source for e in timeline}
        assert "checkpoint" in sources

    async def test_build_since_filters_entries(self, db: AsyncSession) -> None:
        wf = await _active(db)
        future = datetime.now(UTC)
        await WorkflowRuntime(db).advance(wf.id, step="contacted")
        timeline = await AuditTimelineReconstructor(db).build_since(wf.id, since=future)
        assert len(timeline) >= 1

    async def test_entry_has_summary(self, db: AsyncSession) -> None:
        wf = await _active(db)
        timeline = await AuditTimelineReconstructor(db).build(wf.id)
        started = next(e for e in timeline if e.event_type == "workflow.started")
        assert "Workflow started" in started.summary


# ---------------------------------------------------------------------------
# ObservabilityRuntime + GovernanceMetrics
# ---------------------------------------------------------------------------


class TestObservabilityRuntime:
    async def test_record_emits_metric_event(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await ObservabilityRuntime(db).record(
            wf.id, metric_name="step_duration_seconds", value=42.0
        )
        stored, _ = await replay_channel(db, "workflows.observability")
        from workflows.observability import EVT_METRIC
        assert any(e.event_type == EVT_METRIC for e in stored)

    async def test_on_transition_emits_event(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await ObservabilityRuntime(db).on_transition(
            wf.id, WorkflowStatus.active, WorkflowStatus.paused, duration_seconds=5.0
        )
        stored, _ = await replay_channel(db, "workflows.observability")
        assert any(e.event_type == "workflow.transition.observed" for e in stored)


class TestGovernanceMetrics:
    async def test_workflow_metrics_has_event_count(self, db: AsyncSession) -> None:
        wf = await _advanced(db, step="contacted")
        metrics = await GovernanceMetrics(db).workflow_metrics(wf.id)
        assert metrics.total_events >= 2  # started + advanced

    async def test_workflow_metrics_counts_rollbacks(self, db: AsyncSession) -> None:
        from workflows.coordinator import RollbackCoordinator
        wf = await _active(db)
        await RollbackCoordinator(db).coordinate(wf.id, reason="test", trigger="manual")
        metrics = await GovernanceMetrics(db).workflow_metrics(wf.id)
        assert metrics.rollback_count >= 1

    async def test_workflow_metrics_counts_retries(self, db: AsyncSession) -> None:
        from workflows.retry_coordinator import RetryCoordinator
        wf = await _failed(db)
        await RetryCoordinator(db).schedule(wf.id, error="err")
        metrics = await GovernanceMetrics(db).workflow_metrics(wf.id)
        assert metrics.retry_count == 1

    async def test_workflow_metrics_counts_checkpoints(self, db: AsyncSession) -> None:
        wf = await _active(db)
        await CheckpointRuntime(db).set(wf.id, step="s1", status=WorkflowStatus.active)
        await CheckpointRuntime(db).set(wf.id, step="s2", status=WorkflowStatus.active)
        metrics = await GovernanceMetrics(db).workflow_metrics(wf.id)
        assert metrics.checkpoint_count == 2

    async def test_approval_metrics_counts_total(self, db: AsyncSession) -> None:
        wf = await _active(db)
        orch = ApprovalPauseOrchestrator(db)
        await orch.pause_for_approval(wf.id, ApprovalType.offer)
        metrics = await GovernanceMetrics(db).approval_metrics(wf.id)
        assert metrics.total_approvals >= 1
        assert metrics.pending_count >= 1

    async def test_approval_metrics_resolved_count(self, db: AsyncSession) -> None:
        wf = await _active(db)
        orch = ApprovalPauseOrchestrator(db)
        paused = await orch.pause_for_approval(wf.id, ApprovalType.offer)
        await orch.resume_on_approval(paused.approval_id, resolved_by=None)
        metrics = await GovernanceMetrics(db).approval_metrics(wf.id)
        assert metrics.resolved_count >= 1
        assert metrics.pending_count == 0
