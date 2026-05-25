"""
ResumeValidator — pre-resume precondition checks.

Validates all conditions must be met before a workflow can be resumed.
Read-only: no state mutations. Returns ResumeValidation with blockers list.

Strategies:
  checkpoint_restore — can resume via checkpoint (failed workflow with checkpoint)
  direct_resume      — can resume directly (paused workflow, no blockers)
  none               — cannot resume (terminal or unresolvable)
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

# Failed is recoverable via checkpoint; only completed/cancelled are truly terminal
_TRULY_TERMINAL = frozenset({WorkflowStatus.completed, WorkflowStatus.cancelled})


@dataclass(frozen=True)
class ResumeValidation:
    workflow_id: UUID
    can_resume: bool
    recommended_strategy: str  # "checkpoint_restore" | "direct_resume" | "none"
    blockers: list[str]
    warnings: list[str]


class ResumeValidator:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)
        self._checkpoints = CheckpointRuntime(session)
        self._approvals = ApprovalRepository(session)
        self._lease = LeaseRuntime(session)

    async def validate(self, workflow_id: UUID) -> ResumeValidation:
        """
        Check all preconditions for resuming workflow_id.
        Returns ResumeValidation with blockers and recommended strategy.
        """
        blockers: list[str] = []
        warnings: list[str] = []

        wf = await self._repo.get_by_id_or_raise(workflow_id)

        # Truly terminal check (completed/cancelled — not failed, which is recoverable)
        if wf.workflow_status in _TRULY_TERMINAL:
            blockers.append(f"workflow is terminal ({wf.workflow_status})")
            return ResumeValidation(
                workflow_id=workflow_id,
                can_resume=False,
                recommended_strategy="none",
                blockers=blockers,
                warnings=warnings,
            )

        # Already active
        if wf.workflow_status == WorkflowStatus.active:
            blockers.append("workflow is already active")
            return ResumeValidation(
                workflow_id=workflow_id,
                can_resume=False,
                recommended_strategy="none",
                blockers=blockers,
                warnings=warnings,
            )

        # Pending approval blocks direct resume
        all_approvals = await self._approvals.get_by_workflow(workflow_id)
        pending = [
            a for a in all_approvals
            if a.approval_status in (ApprovalStatus.pending, ApprovalStatus.escalated)
        ]
        if pending:
            blockers.append(
                f"{len(pending)} pending approval(s) must be resolved before resuming"
            )

        # Active lease held by another worker
        active_lease = await self._lease.get_active(workflow_id)
        if active_lease:
            warnings.append(
                f"active lease held by {active_lease.holder!r} — "
                "ensure holder is aware of resume"
            )

        # Determine strategy
        if wf.workflow_status == WorkflowStatus.failed:
            checkpoint = await self._checkpoints.get_latest(workflow_id)
            if checkpoint is None:
                blockers.append("no checkpoint found — cannot restore execution context")
            strategy = "checkpoint_restore" if checkpoint else "none"
        else:
            # paused
            strategy = "direct_resume" if not blockers else "none"

        return ResumeValidation(
            workflow_id=workflow_id,
            can_resume=len(blockers) == 0,
            recommended_strategy=strategy,
            blockers=blockers,
            warnings=warnings,
        )
