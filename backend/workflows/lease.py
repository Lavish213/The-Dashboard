"""
LeaseRuntime — workflow execution lease manager.

Prevents concurrent execution of the same workflow across workers.
Lease is identified by lease_id (rotates on each acquire) and holder
(worker identity string). Expired leases can be stolen by new holders.

Invariants:
- One lease row per workflow (unique constraint)
- lease_id mismatch on renew/release → LeaseConflictError (stolen)
- Active unexpired lease from another holder → LeaseAcquireError
- expire_stale() is idempotent and skip-locked for concurrent safety
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from events.contracts import DomainEvent
from events.emitter import event_emitter
from models.enums import LeaseStatus
from models.workflow_lease import WorkflowLease
from workflows.persistence import WorkflowRepository

logger = structlog.get_logger(__name__)

LEASE_CHANNEL = "workflows"
EVT_LEASE_ACQUIRED = "workflow.lease.acquired"
EVT_LEASE_RENEWED = "workflow.lease.renewed"
EVT_LEASE_RELEASED = "workflow.lease.released"
EVT_LEASE_EXPIRED = "workflow.lease.expired"

DEFAULT_TTL_SECONDS = 300  # 5 minutes


class LeaseAcquireError(Exception):
    """Active lease held by another holder that hasn't expired."""

    def __init__(self, workflow_id: uuid.UUID, holder: str, expires_at: datetime) -> None:
        super().__init__(
            f"Lease for {workflow_id} held by {holder!r} until {expires_at.isoformat()}"
        )
        self.workflow_id = workflow_id
        self.holder = holder
        self.expires_at = expires_at


class LeaseConflictError(Exception):
    """lease_id mismatch on renew or release — lease was replaced."""


@dataclass(frozen=True)
class LeaseResult:
    workflow_id: uuid.UUID
    lease_id: uuid.UUID
    holder: str
    expires_at: datetime
    was_renewed: bool = False


class LeaseRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)

    async def acquire(
        self,
        workflow_id: uuid.UUID,
        holder: str,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> LeaseResult:
        """
        Acquire execution lease. SELECT FOR UPDATE prevents concurrent acquisition.
        - No existing lease or expired: creates / overwrites with new lease_id.
        - Active unexpired lease by same holder: refreshes TTL.
        - Active unexpired lease by different holder: raises LeaseAcquireError.
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=ttl_seconds)
        new_lease_id = uuid.uuid4()

        result = await self._session.execute(
            select(WorkflowLease)
            .where(WorkflowLease.workflow_id == workflow_id)
            .with_for_update()
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            if (
                existing.status == LeaseStatus.active
                and existing.expires_at > now
                and existing.holder != holder
            ):
                raise LeaseAcquireError(workflow_id, existing.holder, existing.expires_at)

            existing.lease_id = new_lease_id
            existing.holder = holder
            existing.acquired_at = now
            existing.expires_at = expires_at
            existing.renewed_at = None
            existing.released_at = None
            existing.status = LeaseStatus.active
            self._session.add(existing)
        else:
            self._session.add(
                WorkflowLease(
                    workflow_id=workflow_id,
                    lease_id=new_lease_id,
                    holder=holder,
                    acquired_at=now,
                    expires_at=expires_at,
                    status=LeaseStatus.active,
                )
            )

        await self._session.flush()

        wf = await self._repo.get_by_id_or_raise(workflow_id)
        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=LEASE_CHANNEL,
                event_type=EVT_LEASE_ACQUIRED,
                payload={
                    "workflow_id": str(workflow_id),
                    "lease_id": str(new_lease_id),
                    "holder": holder,
                    "expires_at": expires_at.isoformat(),
                },
                correlation_id=str(wf.correlation_id),
            ),
        )

        logger.info("lease.acquired", workflow_id=str(workflow_id), holder=holder)
        return LeaseResult(
            workflow_id=workflow_id,
            lease_id=new_lease_id,
            holder=holder,
            expires_at=expires_at,
        )

    async def renew(
        self,
        workflow_id: uuid.UUID,
        lease_id: uuid.UUID,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> LeaseResult:
        """Extend lease TTL. Raises LeaseConflictError on lease_id mismatch."""
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(WorkflowLease)
            .where(WorkflowLease.workflow_id == workflow_id)
            .with_for_update()
        )
        lease = result.scalar_one_or_none()

        if lease is None or lease.lease_id != lease_id:
            raise LeaseConflictError(
                f"Lease {lease_id} for {workflow_id} not found or was replaced"
            )

        new_expires = now + timedelta(seconds=ttl_seconds)
        lease.expires_at = new_expires
        lease.renewed_at = now
        lease.status = LeaseStatus.active
        self._session.add(lease)
        await self._session.flush()

        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=LEASE_CHANNEL,
                event_type=EVT_LEASE_RENEWED,
                payload={
                    "workflow_id": str(workflow_id),
                    "lease_id": str(lease_id),
                    "holder": lease.holder,
                    "new_expires_at": new_expires.isoformat(),
                },
            ),
        )

        return LeaseResult(
            workflow_id=workflow_id,
            lease_id=lease_id,
            holder=lease.holder,
            expires_at=new_expires,
            was_renewed=True,
        )

    async def release(
        self,
        workflow_id: uuid.UUID,
        lease_id: uuid.UUID,
    ) -> None:
        """
        Release lease. Idempotent on already-released.
        Raises LeaseConflictError if lease_id doesn't match current lease.
        """
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(WorkflowLease)
            .where(WorkflowLease.workflow_id == workflow_id)
            .with_for_update()
        )
        lease = result.scalar_one_or_none()

        if lease is None:
            return  # idempotent

        if lease.lease_id != lease_id:
            raise LeaseConflictError(
                f"Lease {lease_id} for {workflow_id} was replaced — cannot release"
            )

        if lease.status == LeaseStatus.released:
            return  # idempotent

        lease.status = LeaseStatus.released
        lease.released_at = now
        self._session.add(lease)
        await self._session.flush()

        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=LEASE_CHANNEL,
                event_type=EVT_LEASE_RELEASED,
                payload={
                    "workflow_id": str(workflow_id),
                    "lease_id": str(lease_id),
                    "holder": lease.holder,
                },
            ),
        )

        logger.info("lease.released", workflow_id=str(workflow_id))

    async def get_active(self, workflow_id: uuid.UUID) -> LeaseResult | None:
        """Return active non-expired lease, or None."""
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(WorkflowLease).where(
                WorkflowLease.workflow_id == workflow_id,
                WorkflowLease.status == LeaseStatus.active,
                WorkflowLease.expires_at > now,
            )
        )
        lease = result.scalar_one_or_none()
        if lease is None:
            return None
        return LeaseResult(
            workflow_id=workflow_id,
            lease_id=lease.lease_id,
            holder=lease.holder,
            expires_at=lease.expires_at,
        )

    async def expire_stale(self, now: datetime | None = None) -> list[uuid.UUID]:
        """
        Mark active leases past expires_at as expired.
        skip_locked: safe for concurrent workers running expiry sweeps.
        Returns affected workflow_ids for follow-up orphaned recovery.
        """
        cutoff = now or datetime.now(UTC)
        result = await self._session.execute(
            select(WorkflowLease)
            .where(
                WorkflowLease.status == LeaseStatus.active,
                WorkflowLease.expires_at <= cutoff,
            )
            .with_for_update(skip_locked=True)
        )
        stale = list(result.scalars().all())
        expired_ids: list[uuid.UUID] = []

        for lease in stale:
            lease.status = LeaseStatus.expired
            self._session.add(lease)
            expired_ids.append(lease.workflow_id)

        if stale:
            await self._session.flush()
            for wf_id in expired_ids:
                await event_emitter.emit(
                    self._session,
                    DomainEvent(
                        channel=LEASE_CHANNEL,
                        event_type=EVT_LEASE_EXPIRED,
                        payload={"workflow_id": str(wf_id)},
                    ),
                )

        logger.info("lease.expire_stale", count=len(expired_ids))
        return expired_ids
