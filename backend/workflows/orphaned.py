"""
OrphanedRecovery — recover workflows whose execution lease expired.

An orphaned workflow had an active execution lease that expired (worker crash).
Recovery: resume from latest checkpoint if available, else cancel.

find_orphaned() only returns workflows that were actively leased (lease exists
in expired state) and are still in a non-terminal status.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from events.contracts import DomainEvent
from events.emitter import event_emitter
from models.enums import AuditActorType, LeaseStatus, WorkflowStatus
from models.workflow import Workflow
from models.workflow_lease import WorkflowLease
from workflows.persistence import WorkflowRepository
from workflows.recovery import CheckpointRecoveryResult, WorkflowRecovery
from workflows.runtime import WorkflowRuntime

logger = structlog.get_logger(__name__)

ORPHAN_CHANNEL = "workflows"
EVT_ORPHANED_DETECTED = "workflow.orphaned.detected"
EVT_ORPHANED_RECOVERED = "workflow.orphaned.recovered"
EVT_ORPHANED_CANCELLED = "workflow.orphaned.cancelled"


@dataclass(frozen=True)
class OrphanedWorkflow:
    workflow_id: UUID
    current_step: str | None
    current_status: WorkflowStatus
    lease_expired_at: datetime


class OrphanedRecovery:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)
        self._recovery = WorkflowRecovery(session)
        self._runtime = WorkflowRuntime(session)

    async def find_orphaned(self) -> list[OrphanedWorkflow]:
        """
        Find active/paused workflows with expired leases.
        Only workflows that were actively leased (had a lease) qualify.
        """
        result = await self._session.execute(
            select(Workflow, WorkflowLease.expires_at)
            .join(WorkflowLease, Workflow.id == WorkflowLease.workflow_id)
            .where(
                Workflow.workflow_status.in_([WorkflowStatus.active, WorkflowStatus.paused]),
                WorkflowLease.status == LeaseStatus.expired,
            )
        )

        return [
            OrphanedWorkflow(
                workflow_id=wf.id,
                current_step=wf.current_step,
                current_status=wf.workflow_status,
                lease_expired_at=lease_expired_at,
            )
            for wf, lease_expired_at in result.all()
        ]

    async def recover(
        self,
        workflow_id: UUID,
        actor_id: UUID | None = None,
    ) -> CheckpointRecoveryResult | None:
        """
        Attempt recovery of an orphaned workflow.
        - Checkpoint exists: resume from checkpoint → EVT_ORPHANED_RECOVERED
        - No checkpoint: cancel workflow → EVT_ORPHANED_CANCELLED
        Returns CheckpointRecoveryResult if recovered, None if cancelled.
        """
        wf = await self._repo.get_by_id_or_raise(workflow_id)

        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=ORPHAN_CHANNEL,
                event_type=EVT_ORPHANED_DETECTED,
                payload={
                    "workflow_id": str(workflow_id),
                    "current_step": wf.current_step,
                    "current_status": str(wf.workflow_status),
                },
                correlation_id=str(wf.correlation_id),
            ),
        )

        try:
            result = await self._recovery.resume_from_checkpoint(
                workflow_id, actor_id=actor_id
            )
            await event_emitter.emit(
                self._session,
                DomainEvent(
                    channel=ORPHAN_CHANNEL,
                    event_type=EVT_ORPHANED_RECOVERED,
                    payload={
                        "workflow_id": str(workflow_id),
                        "restored_from_step": result.restored_from_step,
                    },
                    correlation_id=str(wf.correlation_id),
                ),
            )
            logger.info("orphan.recovered", workflow_id=str(workflow_id))
            return result

        except Exception:
            # No checkpoint or already terminal — cancel if still non-terminal
            try:
                await self._runtime.cancel(
                    workflow_id,
                    reason="orphaned_no_checkpoint",
                    actor_type=AuditActorType.system,
                    actor_id=actor_id,
                )
            except Exception:
                pass  # already terminal

            await event_emitter.emit(
                self._session,
                DomainEvent(
                    channel=ORPHAN_CHANNEL,
                    event_type=EVT_ORPHANED_CANCELLED,
                    payload={
                        "workflow_id": str(workflow_id),
                        "reason": "no_checkpoint",
                    },
                    correlation_id=str(wf.correlation_id),
                ),
            )
            logger.warning("orphan.cancelled", workflow_id=str(workflow_id))
            return None
