"""
ContextRetentionRuntime — lifecycle management for context snapshots.

Applies ContextRetentionPolicy to determine which snapshots should be
archived or expired. Enforces explicit-delete guard when configured.

find_archivable(policy, now) → list[ContextSnapshot] — candidates to archive.
find_expirable(policy, now) → list[ContextSnapshot] — candidates to expire.
archive(snapshot) — transition active → archived.
expire(snapshot) — transition active/archived → expired.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from context.contracts import ContextRetentionPolicy
from models.context_snapshot import ContextSnapshot
from models.enums import ContextSnapshotStatus


class RetentionViolationError(Exception):
    """Raised when explicit-delete guard blocks automatic expiry."""

    def __init__(self, snapshot_id) -> None:
        self.snapshot_id = snapshot_id
        super().__init__(
            f"Snapshot {snapshot_id} requires explicit delete — "
            "set requires_explicit_delete=False to allow automatic expiry"
        )


class ContextRetentionRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_archivable(
        self,
        policy: ContextRetentionPolicy,
        now: datetime | None = None,
    ) -> list[ContextSnapshot]:
        """Return active snapshots older than archive_after_days."""
        if policy.archive_after_days is None:
            return []
        now = now or datetime.now(UTC)
        cutoff = now - timedelta(days=policy.archive_after_days)
        result = await self._session.execute(
            select(ContextSnapshot).where(
                ContextSnapshot.status == ContextSnapshotStatus.active,
                ContextSnapshot.created_at < cutoff,
            )
        )
        return list(result.scalars().all())

    async def find_expirable(
        self,
        policy: ContextRetentionPolicy,
        now: datetime | None = None,
    ) -> list[ContextSnapshot]:
        """Return active/archived snapshots older than expire_after_days."""
        if policy.expire_after_days is None:
            return []
        if policy.requires_explicit_delete:
            raise RetentionViolationError("policy")
        now = now or datetime.now(UTC)
        cutoff = now - timedelta(days=policy.expire_after_days)
        result = await self._session.execute(
            select(ContextSnapshot).where(
                ContextSnapshot.status.in_(
                    [ContextSnapshotStatus.active, ContextSnapshotStatus.archived]
                ),
                ContextSnapshot.created_at < cutoff,
            )
        )
        return list(result.scalars().all())

    async def archive(self, snapshot: ContextSnapshot) -> ContextSnapshot:
        """Transition status active → archived."""
        snapshot.status = ContextSnapshotStatus.archived
        self._session.add(snapshot)
        await self._session.flush()
        await self._session.refresh(snapshot)
        return snapshot

    async def expire(
        self,
        snapshot: ContextSnapshot,
        policy: ContextRetentionPolicy | None = None,
    ) -> ContextSnapshot:
        """
        Transition status → expired.
        Raises RetentionViolationError if policy.requires_explicit_delete=True.
        """
        if policy is not None and policy.requires_explicit_delete:
            raise RetentionViolationError(snapshot.id)
        snapshot.status = ContextSnapshotStatus.expired
        self._session.add(snapshot)
        await self._session.flush()
        await self._session.refresh(snapshot)
        return snapshot
