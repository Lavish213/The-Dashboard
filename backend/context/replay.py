"""
ContextReplayRuntime — replay-safe deterministic context reconstruction.

Reconstructs ContextAssemblyResult from a persisted snapshot without
touching live data. Snapshot contents are fixed at creation time —
replay always produces the same window given the same snapshot.

Replay is blocked for expired or archived snapshots (fail-closed).

reconstruct(snapshot_id) → ContextAssemblyResult
reconstruct_by_key(assembly_key) → ContextAssemblyResult
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from context.contracts import ContextAssemblyResult
from context.exceptions import ContextReplayError
from context.snapshot import ContextSnapshotRuntime
from models.enums import ContextSnapshotStatus
from repositories.context_snapshot import ContextSnapshotRepository


class ContextReplayRuntime:
    """
    Deterministic context replay — no live data access during reconstruction.

    Raises ContextReplayError if snapshot not found, expired, or archived.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._snapshot_runtime = ContextSnapshotRuntime(session)
        self._repo = ContextSnapshotRepository(session)

    async def reconstruct(self, snapshot_id: UUID) -> ContextAssemblyResult:
        """
        Reconstruct ContextAssemblyResult from snapshot_id.
        Raises ContextReplayError if not found, expired, or archived.
        """
        snapshot = await self._repo.get_by_id(snapshot_id)
        if snapshot is None:
            raise ContextReplayError(
                snapshot_id=snapshot_id,
                reason="snapshot not found",
            )
        self._assert_replayable(snapshot)
        result = self._snapshot_runtime._to_result(snapshot)
        return result

    async def reconstruct_by_key(self, assembly_key: str) -> ContextAssemblyResult:
        """
        Reconstruct ContextAssemblyResult by assembly_key.
        Raises ContextReplayError if not found, expired, or archived.
        """
        snapshot = await self._repo.get_by_key(assembly_key)
        if snapshot is None:
            raise ContextReplayError(
                snapshot_id=assembly_key,
                reason="snapshot not found",
            )
        self._assert_replayable(snapshot)
        result = self._snapshot_runtime._to_result(snapshot)
        return result

    def _assert_replayable(self, snapshot) -> None:
        """
        Fail-closed: only active snapshots are replayable.
        Expired and archived snapshots are blocked.
        """
        if snapshot.status == ContextSnapshotStatus.expired:
            raise ContextReplayError(
                snapshot_id=snapshot.id,
                reason="snapshot is expired — replay blocked",
            )
        if snapshot.status == ContextSnapshotStatus.archived:
            raise ContextReplayError(
                snapshot_id=snapshot.id,
                reason="snapshot is archived — replay blocked",
            )
