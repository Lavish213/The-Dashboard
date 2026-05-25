"""
ContextSnapshotRepository — data access for context_snapshots table.

Extends BaseRepository with:
  get_by_key(assembly_key) — idempotency lookup.
  get_active_for_workflow(workflow_id) — latest active snapshot per workflow.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.context_snapshot import ContextSnapshot
from models.enums import ContextSnapshotStatus
from repositories.base import BaseRepository


class ContextSnapshotRepository(BaseRepository[ContextSnapshot]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ContextSnapshot)

    async def get_by_key(self, assembly_key: str) -> ContextSnapshot | None:
        """Return existing snapshot by idempotency key, or None."""
        result = await self.session.execute(
            select(ContextSnapshot).where(
                ContextSnapshot.assembly_key == assembly_key
            )
        )
        return result.scalar_one_or_none()

    async def get_active_for_workflow(
        self, workflow_id: UUID
    ) -> list[ContextSnapshot]:
        """Return all active snapshots linked to workflow_id, newest first."""
        result = await self.session.execute(
            select(ContextSnapshot)
            .where(
                ContextSnapshot.workflow_id == workflow_id,
                ContextSnapshot.status == ContextSnapshotStatus.active,
            )
            .order_by(ContextSnapshot.created_at.desc())
        )
        return list(result.scalars().all())
