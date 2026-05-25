"""
Execution integrity assertions — replay verification, consistency validation,
and cross-runtime integrity checks.

ReplayVerifier       — verify replay-derived state matches expected values
ConsistencyValidator — comprehensive multi-dimension consistency report
CrossRuntimeAssertions — assert internal consistency across leases/approvals/checkpoints

All operations are read-only. No DB mutations.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import ApprovalStatus, WorkflowStatus
from repositories.approval import ApprovalRepository
from workflows.checkpoint import CheckpointRuntime
from workflows.lease import LeaseRuntime
from workflows.persistence import WorkflowRepository
from workflows.recovery import WorkflowRecovery
from workflows.states import TERMINAL_STATES

# ---------------------------------------------------------------------------
# ReplayVerifier
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReplayVerification:
    workflow_id: UUID
    is_valid: bool
    expected_status: WorkflowStatus
    derived_status: WorkflowStatus
    expected_step: str | None
    derived_step: str | None
    event_count: int
    violations: list[str]


class ReplayVerifier:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._recovery = WorkflowRecovery(session)

    async def verify(
        self,
        workflow_id: UUID,
        expected_status: WorkflowStatus,
        expected_step: str | None = None,
    ) -> ReplayVerification:
        """
        Replay event log and verify derived state matches expectations.
        Violations list is empty on success.
        """
        replay = await self._recovery.replay(workflow_id)
        violations: list[str] = []

        if replay.final_status != expected_status:
            violations.append(
                f"status mismatch: expected {expected_status!r}, "
                f"got {replay.final_status!r}"
            )

        if expected_step is not None and replay.final_step != expected_step:
            violations.append(
                f"step mismatch: expected {expected_step!r}, "
                f"got {replay.final_step!r}"
            )

        return ReplayVerification(
            workflow_id=workflow_id,
            is_valid=len(violations) == 0,
            expected_status=expected_status,
            derived_status=replay.final_status,
            expected_step=expected_step,
            derived_step=replay.final_step,
            event_count=replay.replayed_events,
            violations=violations,
        )


# ---------------------------------------------------------------------------
# ConsistencyValidator
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsistencyReport:
    workflow_id: UUID
    is_consistent: bool
    state_consistent: bool        # replay matches persisted status+step
    approval_consistent: bool     # paused iff pending approval
    checkpoint_recoverable: bool  # if failed, checkpoint exists
    findings: list[str]


class ConsistencyValidator:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)
        self._recovery = WorkflowRecovery(session)
        self._checkpoints = CheckpointRuntime(session)
        self._approvals = ApprovalRepository(session)

    async def validate(self, workflow_id: UUID) -> ConsistencyReport:
        """Comprehensive consistency check across state, approvals, and checkpoints."""
        findings: list[str] = []
        wf = await self._repo.get_by_id_or_raise(workflow_id)

        # 1. State consistency (replay vs persisted)
        consistency = await self._recovery.consistency_check(workflow_id)
        state_ok = consistency.is_consistent
        if not state_ok:
            findings.append(
                f"state drift: persisted={wf.workflow_status}/{wf.current_step} "
                f"derived={consistency.derived_status}/{consistency.derived_step}"
            )

        # 2. Approval consistency: paused ↔ pending approval
        all_approvals = await self._approvals.get_by_workflow(workflow_id)
        has_pending = any(
            a.approval_status in (ApprovalStatus.pending, ApprovalStatus.escalated)
            for a in all_approvals
        )
        approval_ok: bool
        if wf.workflow_status == WorkflowStatus.paused and not has_pending:
            findings.append("workflow is paused but has no pending approval")
            approval_ok = False
        elif has_pending and wf.workflow_status not in (
            WorkflowStatus.paused, *TERMINAL_STATES
        ):
            findings.append(
                "pending approval exists but workflow is not paused or terminal"
            )
            approval_ok = False
        else:
            approval_ok = True

        # 3. Checkpoint recoverability: failed → checkpoint exists
        checkpoint_ok: bool
        if wf.workflow_status == WorkflowStatus.failed:
            checkpoint = await self._checkpoints.get_latest(workflow_id)
            checkpoint_ok = checkpoint is not None
            if not checkpoint_ok:
                findings.append(
                    "workflow is failed but has no checkpoint — "
                    "cannot be recovered via checkpoint restore"
                )
        else:
            checkpoint_ok = True

        all_ok = state_ok and approval_ok and checkpoint_ok
        return ConsistencyReport(
            workflow_id=workflow_id,
            is_consistent=all_ok,
            state_consistent=state_ok,
            approval_consistent=approval_ok,
            checkpoint_recoverable=checkpoint_ok,
            findings=findings,
        )


# ---------------------------------------------------------------------------
# CrossRuntimeAssertions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AssertionReport:
    workflow_id: UUID
    all_passed: bool
    passed: list[str]
    failed: list[str]
    warnings: list[str]


class CrossRuntimeAssertions:
    """
    Assert invariants that span workflows, approvals, checkpoints, and leases.
    All assertions are advisory — failures are reported, not raised.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)
        self._checkpoints = CheckpointRuntime(session)
        self._approvals = ApprovalRepository(session)
        self._lease = LeaseRuntime(session)
        self._recovery = WorkflowRecovery(session)

    async def assert_all(self, workflow_id: UUID) -> AssertionReport:
        """Run all cross-runtime assertions. Returns report with pass/fail/warnings."""
        passed: list[str] = []
        failed: list[str] = []
        warnings: list[str] = []

        wf = await self._repo.get_by_id_or_raise(workflow_id)

        # A1: State is event-derivable
        try:
            consistency = await self._recovery.consistency_check(workflow_id)
            if consistency.is_consistent:
                passed.append("A1:state_derivable")
            else:
                failed.append(
                    "A1:state_derivable — persisted state diverges from event log"
                )
        except Exception as exc:  # noqa: BLE001
            failed.append(f"A1:state_derivable — error: {exc}")

        # A2: Terminal workflows have no active leases
        if wf.workflow_status in TERMINAL_STATES:
            active_lease = await self._lease.get_active(workflow_id)
            if active_lease is None:
                passed.append("A2:terminal_no_active_lease")
            else:
                warnings.append(
                    f"A2:terminal_no_active_lease — terminal workflow has active lease "
                    f"(holder={active_lease.holder!r})"
                )

        # A3: Paused workflows have at least one pending/escalated approval
        if wf.workflow_status == WorkflowStatus.paused:
            all_approvals = await self._approvals.get_by_workflow(workflow_id)
            has_pending = any(
                a.approval_status in (ApprovalStatus.pending, ApprovalStatus.escalated)
                for a in all_approvals
            )
            if has_pending:
                passed.append("A3:paused_has_pending_approval")
            else:
                warnings.append(
                    "A3:paused_has_pending_approval — paused but no pending approval"
                )

        # A4: Checkpoints are ordered (no created_at inversion)
        checkpoints = await self._checkpoints.get_all(workflow_id)
        if len(checkpoints) >= 2:
            ordered = all(
                checkpoints[i].created_at <= checkpoints[i + 1].created_at
                for i in range(len(checkpoints) - 1)
            )
            if ordered:
                passed.append("A4:checkpoints_ordered")
            else:
                failed.append("A4:checkpoints_ordered — checkpoint timestamps not monotonic")
        else:
            passed.append("A4:checkpoints_ordered")  # trivially true

        # A5: Failed + no checkpoint = unrecoverable (warning only)
        if wf.workflow_status == WorkflowStatus.failed:
            latest_cp = await self._checkpoints.get_latest(workflow_id)
            if latest_cp is None:
                warnings.append(
                    "A5:failed_recoverable — failed workflow has no checkpoint; "
                    "requires manual intervention"
                )
            else:
                passed.append("A5:failed_recoverable")

        all_passed = len(failed) == 0
        return AssertionReport(
            workflow_id=workflow_id,
            all_passed=all_passed,
            passed=passed,
            failed=failed,
            warnings=warnings,
        )
