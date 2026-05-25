"""
CheckpointRuntime — set and retrieve workflow step checkpoints.

Checkpoints are append-only. Setting a checkpoint at an existing step is a no-op
(idempotent). Callers should set checkpoints after each significant step advance.

Supports:
- get_latest: last checkpoint before current position (rollback target)
- get_all: full ordered history (replay validation)
- resume_payload: payload from most recent checkpoint for context restore
"""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import WorkflowStatus
from models.workflow_checkpoint import WorkflowCheckpoint

logger = structlog.get_logger(__name__)


class CheckpointRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def set(
        self,
        workflow_id: UUID,
        step: str,
        status: WorkflowStatus,
        payload: dict | None = None,
    ) -> WorkflowCheckpoint:
        """
        Record a checkpoint at `step`. Idempotent — duplicate (workflow, step) is ignored.
        Returns the existing checkpoint if already set, new one otherwise.
        """
        existing = await self._get_by_step(workflow_id, step)
        if existing is not None:
            return existing

        checkpoint = WorkflowCheckpoint(
            workflow_id=workflow_id,
            step=step,
            status_at_checkpoint=status.value,
            payload=payload or {},
        )
        self._session.add(checkpoint)
        try:
            await self._session.flush()
        except IntegrityError:
            # Race: another writer set the same checkpoint — fetch it
            await self._session.rollback()
            existing = await self._get_by_step(workflow_id, step)
            if existing is None:
                raise
            return existing

        logger.info(
            "workflow.checkpoint.set",
            workflow_id=str(workflow_id),
            step=step,
            status=status.value,
        )
        return checkpoint

    async def get_latest(self, workflow_id: UUID) -> WorkflowCheckpoint | None:
        """Return the most recently created checkpoint for this workflow."""
        result = await self._session.execute(
            select(WorkflowCheckpoint)
            .where(WorkflowCheckpoint.workflow_id == workflow_id)
            .order_by(WorkflowCheckpoint.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all(self, workflow_id: UUID) -> list[WorkflowCheckpoint]:
        """Return all checkpoints ordered by creation time (earliest first)."""
        result = await self._session.execute(
            select(WorkflowCheckpoint)
            .where(WorkflowCheckpoint.workflow_id == workflow_id)
            .order_by(WorkflowCheckpoint.created_at.asc())
        )
        return list(result.scalars().all())

    async def _get_by_step(
        self, workflow_id: UUID, step: str
    ) -> WorkflowCheckpoint | None:
        result = await self._session.execute(
            select(WorkflowCheckpoint).where(
                WorkflowCheckpoint.workflow_id == workflow_id,
                WorkflowCheckpoint.step == step,
            )
        )
        return result.scalar_one_or_none()
