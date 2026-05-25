"""
ResearchMemory — scoped runtime memory for a research job or task.

Temporary only — TTL enforced at read time.
No embeddings, no semantic retrieval.
Scoped to job, task, or session. Cleaned up on job termination.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base
from models.enums import ResearchMemoryScope


class ResearchMemory(Base):
    __tablename__ = "research_memory"

    __table_args__ = (
        sa.UniqueConstraint(
            "job_id",
            "scope",
            "memory_key",
            "task_id",
            name="uq_research_memory_key",
        ),
        sa.Index("ix_research_memory_job_id", "job_id"),
        sa.Index("ix_research_memory_expires_at", "expires_at"),
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
    # Advisory task scope — no FK
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    scope: Mapped[ResearchMemoryScope] = mapped_column(
        sa.Enum(ResearchMemoryScope, native_enum=True),
        nullable=False,
    )
    memory_key: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # TTL — None means no expiry
    expires_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        onupdate=func.clock_timestamp(),
        nullable=False,
    )
