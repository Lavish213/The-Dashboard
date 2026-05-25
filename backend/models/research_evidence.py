"""
ResearchEvidence — immutable evidence record captured during a research job.

content_hash enables deduplication within a job.
provenance blob captures: who, when, how evidence was collected.
snapshot blob is the immutable captured state at collection time.
score is a float relevance measure [0.0, 1.0].
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base
from models.enums import ResearchEvidenceStatus


class ResearchEvidence(Base):
    __tablename__ = "research_evidence"

    __table_args__ = (
        sa.Index("ix_research_evidence_job_id", "job_id"),
        sa.Index("ix_research_evidence_status", "status"),
        sa.Index("ix_research_evidence_content_hash", "content_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("research_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Advisory task reference — no FK
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    status: Mapped[ResearchEvidenceStatus] = mapped_column(
        sa.Enum(ResearchEvidenceStatus, native_enum=True),
        nullable=False,
        default=ResearchEvidenceStatus.pending,
    )
    # Source identification
    source_uri: Mapped[str] = mapped_column(sa.Text, nullable=False)
    source_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    # SHA-256 hex digest of content for deduplication
    content_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    # Text excerpt (truncated, not authoritative)
    content_snippet: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # Relevance score 0.0 – 1.0
    score: Mapped[float] = mapped_column(
        sa.Float,
        nullable=False,
        default=0.0,
    )
    # Human-readable citation reference
    citation_ref: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # Provenance: collector, method, timestamps
    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Immutable captured state at collection time
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        nullable=False,
    )
