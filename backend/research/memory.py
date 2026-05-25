"""
ResearchMemoryRuntime — scoped runtime memory for research jobs and tasks.

Temporary only. TTL enforced at read time.
No embeddings, no semantic retrieval.
Deterministic cleanup on job termination via clear_job().
Expired entries are treated as misses — stale data never surfaces.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import ResearchEventType, ResearchMemoryScope
from models.research_memory import ResearchMemory
from repositories.research_event import ResearchEventRepository
from repositories.research_memory import ResearchMemoryRepository
from research.contracts import ResearchMemoryEntry, ResearchMemorySpec


class ResearchMemoryExpiredError(Exception):
    pass


class ResearchMemoryRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._memory = ResearchMemoryRepository(session)
        self._events = ResearchEventRepository(session)

    async def write(self, spec: ResearchMemorySpec) -> ResearchMemoryEntry:
        """
        Write or overwrite a memory entry.
        Upsert semantics: same (job_id, scope, memory_key, task_id) = overwrite.
        """
        expires_at: datetime | None = None
        if spec.ttl_seconds is not None:
            expires_at = datetime.now(UTC) + timedelta(seconds=spec.ttl_seconds)

        existing = await self._memory.get(
            job_id=spec.job_id,
            scope=spec.scope,
            memory_key=spec.memory_key,
            task_id=spec.task_id,
        )
        if existing is not None:
            existing.value = spec.value
            existing.expires_at = expires_at
            self._session.add(existing)
            await self._session.flush()
            row = existing
        else:
            row = ResearchMemory(
                job_id=spec.job_id,
                task_id=spec.task_id,
                scope=spec.scope,
                memory_key=spec.memory_key,
                value=spec.value,
                expires_at=expires_at,
            )
            self._session.add(row)
            await self._session.flush()

        await self._events.append(
            ResearchEventType.memory_written,
            job_id=spec.job_id,
            payload={
                "scope": spec.scope.value,
                "memory_key": spec.memory_key,
                "has_ttl": spec.ttl_seconds is not None,
            },
        )
        return self._to_entry(row)

    async def read(
        self,
        job_id: UUID,
        scope: ResearchMemoryScope,
        memory_key: str,
        task_id: UUID | None = None,
    ) -> ResearchMemoryEntry | None:
        """
        Read a memory entry. Returns None if not found or expired.
        Expired entries are hard-deleted on read (lazy expiry).
        """
        row = await self._memory.get(
            job_id=job_id,
            scope=scope,
            memory_key=memory_key,
            task_id=task_id,
        )
        if row is None:
            return None

        if row.expires_at is not None and row.expires_at <= datetime.now(UTC):
            await self._session.delete(row)
            await self._session.flush()
            await self._events.append(
                ResearchEventType.memory_expired,
                job_id=job_id,
                payload={"scope": scope.value, "memory_key": memory_key},
            )
            return None

        return self._to_entry(row)

    async def clear_job(self, job_id: UUID) -> int:
        """
        Hard-delete all memory entries for a job.
        Called on job completion/cancellation/failure.
        Returns count of deleted entries.
        """
        count = await self._memory.delete_for_job(job_id)
        if count > 0:
            await self._events.append(
                ResearchEventType.memory_cleared,
                job_id=job_id,
                payload={"cleared_count": count},
            )
        return count

    async def expire_stale(self) -> int:
        """
        Sweep expired entries. Returns count deleted.
        Intended for periodic cleanup; safe to call at any time.
        """
        return await self._memory.delete_expired()

    async def list_job(
        self,
        job_id: UUID,
        scope: ResearchMemoryScope | None = None,
        task_id: UUID | None = None,
    ) -> list[ResearchMemoryEntry]:
        """List live (non-expired) memory entries for a job."""
        now = datetime.now(UTC)
        if scope is not None:
            rows = await self._memory.list_by_scope(
                job_id=job_id,
                scope=scope,
                task_id=task_id,
            )
        else:
            rows = await self._memory.list_by_job(job_id)

        live = [
            r for r in rows
            if r.expires_at is None or r.expires_at > now
        ]
        return [self._to_entry(r) for r in live]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _to_entry(self, row: ResearchMemory) -> ResearchMemoryEntry:
        return ResearchMemoryEntry(
            memory_id=row.id,
            job_id=row.job_id,
            scope=row.scope,
            memory_key=row.memory_key,
            value=row.value,
            created_at=row.created_at,
            task_id=row.task_id,
            expires_at=row.expires_at,
        )
