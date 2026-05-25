"""
ResearchEvidenceRuntime — evidence recording, deduplication, and provenance.

Deduplication is content_hash-scoped per job — same hash within one job = duplicate.
Scores are [0.0, 1.0]. Immutable once accepted/rejected.
No embeddings, no semantic search.
"""
from __future__ import annotations

import hashlib
import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import ResearchEventType, ResearchEvidenceStatus
from models.research_evidence import ResearchEvidence
from repositories.research_event import ResearchEventRepository
from repositories.research_evidence import ResearchEvidenceRepository
from research.contracts import ResearchEvidenceRecord, ResearchEvidenceSpec


class ResearchEvidenceError(Exception):
    pass


class ResearchEvidenceRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._evidence = ResearchEvidenceRepository(session)
        self._events = ResearchEventRepository(session)

    async def record(self, spec: ResearchEvidenceSpec) -> ResearchEvidenceRecord:
        """
        Record a piece of evidence. Checks for duplicate within the job.
        Duplicate → returns existing record with status=duplicate (not created again).
        """
        existing = await self._evidence.get_by_hash(spec.job_id, spec.content_hash)
        if existing is not None:
            # Mark as duplicate — emit event but don't insert
            await self._events.append(
                ResearchEventType.evidence_deduplicated,
                job_id=spec.job_id,
                task_id=spec.task_id,
                payload={
                    "duplicate_of": str(existing.id),
                    "content_hash": spec.content_hash,
                    "source_uri": spec.source_uri,
                },
            )
            return self._to_record(existing, override_status=ResearchEvidenceStatus.duplicate)

        row = ResearchEvidence(
            job_id=spec.job_id,
            task_id=spec.task_id,
            status=ResearchEvidenceStatus.pending,
            source_uri=spec.source_uri,
            source_type=spec.source_type,
            content_hash=spec.content_hash,
            content_snippet=spec.content_snippet,
            score=spec.score,
            citation_ref=spec.citation_ref,
            provenance=spec.provenance,
            snapshot=spec.snapshot,
        )
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.evidence_recorded,
            job_id=spec.job_id,
            task_id=spec.task_id,
            payload={
                "evidence_id": str(row.id),
                "source_type": spec.source_type,
                "score": spec.score,
            },
        )
        return self._to_record(row)

    async def accept(
        self,
        evidence_id: UUID,
        actor_id: UUID | None = None,
    ) -> ResearchEvidenceRecord:
        """Mark evidence as accepted."""
        row = await self._evidence.get(evidence_id)
        if row is None:
            raise ResearchEvidenceError(f"Evidence {evidence_id} not found")
        if row.status not in (
            ResearchEvidenceStatus.pending,
            ResearchEvidenceStatus.rejected,
        ):
            raise ResearchEvidenceError(
                f"Cannot accept evidence with status {row.status}"
            )

        row.status = ResearchEvidenceStatus.accepted
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.evidence_accepted,
            job_id=row.job_id,
            task_id=row.task_id,
            actor_id=actor_id,
            payload={"evidence_id": str(evidence_id)},
        )
        return self._to_record(row)

    async def reject(
        self,
        evidence_id: UUID,
        reason: str,
        actor_id: UUID | None = None,
    ) -> ResearchEvidenceRecord:
        """Mark evidence as rejected."""
        row = await self._evidence.get(evidence_id)
        if row is None:
            raise ResearchEvidenceError(f"Evidence {evidence_id} not found")
        if row.status not in (
            ResearchEvidenceStatus.pending,
            ResearchEvidenceStatus.accepted,
        ):
            raise ResearchEvidenceError(
                f"Cannot reject evidence with status {row.status}"
            )

        row.status = ResearchEvidenceStatus.rejected
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            ResearchEventType.evidence_rejected,
            job_id=row.job_id,
            task_id=row.task_id,
            actor_id=actor_id,
            payload={"evidence_id": str(evidence_id), "reason": reason},
        )
        return self._to_record(row)

    async def get_by_job(self, job_id: UUID) -> list[ResearchEvidenceRecord]:
        rows = await self._evidence.list_by_job(job_id)
        return [self._to_record(r) for r in rows]

    async def get_accepted(self, job_id: UUID) -> list[ResearchEvidenceRecord]:
        rows = await self._evidence.list_accepted(job_id)
        return [self._to_record(r) for r in rows]

    @staticmethod
    def compute_hash(content: str | dict) -> str:
        """
        Deterministic SHA-256 content hash for deduplication.
        dict inputs are JSON-serialized with sorted keys for stability.
        """
        if isinstance(content, dict):
            raw = json.dumps(content, sort_keys=True, ensure_ascii=False)
        else:
            raw = content
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _to_record(
        self,
        row: ResearchEvidence,
        override_status: ResearchEvidenceStatus | None = None,
    ) -> ResearchEvidenceRecord:
        return ResearchEvidenceRecord(
            evidence_id=row.id,
            job_id=row.job_id,
            status=override_status if override_status is not None else row.status,
            source_uri=row.source_uri,
            source_type=row.source_type,
            content_hash=row.content_hash,
            score=row.score,
            provenance=row.provenance,
            snapshot=row.snapshot,
            created_at=row.created_at,
            task_id=row.task_id,
            content_snippet=row.content_snippet,
            citation_ref=row.citation_ref,
        )
