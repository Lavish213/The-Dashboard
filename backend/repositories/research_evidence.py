"""
ResearchEvidenceRepository — data access for research evidence records.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import ResearchEvidenceStatus
from models.research_evidence import ResearchEvidence


class ResearchEvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, evidence_id: UUID) -> ResearchEvidence | None:
        result = await self._session.execute(
            select(ResearchEvidence).where(ResearchEvidence.id == evidence_id)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(
        self,
        job_id: UUID,
        content_hash: str,
    ) -> ResearchEvidence | None:
        """Check for an existing evidence record with the same content hash (dedup)."""
        result = await self._session.execute(
            select(ResearchEvidence).where(
                ResearchEvidence.job_id == job_id,
                ResearchEvidence.content_hash == content_hash,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_job(self, job_id: UUID) -> list[ResearchEvidence]:
        result = await self._session.execute(
            select(ResearchEvidence)
            .where(ResearchEvidence.job_id == job_id)
            .order_by(ResearchEvidence.created_at)
        )
        return list(result.scalars().all())

    async def list_by_task(self, task_id: UUID) -> list[ResearchEvidence]:
        result = await self._session.execute(
            select(ResearchEvidence)
            .where(ResearchEvidence.task_id == task_id)
            .order_by(ResearchEvidence.created_at)
        )
        return list(result.scalars().all())

    async def list_accepted(self, job_id: UUID) -> list[ResearchEvidence]:
        result = await self._session.execute(
            select(ResearchEvidence)
            .where(
                ResearchEvidence.job_id == job_id,
                ResearchEvidence.status == ResearchEvidenceStatus.accepted,
            )
            .order_by(ResearchEvidence.score.desc())
        )
        return list(result.scalars().all())
