"""
ResearchTask — one node in a research job's task graph.

Each task has a type, depth, retry budget, and input/output blobs.
Dependencies are tracked in research_task_dependencies.
Idempotent on task_key.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base
from models.enums import ResearchTaskStatus


class ResearchTask(Base):
    __tablename__ = "research_tasks"

    __table_args__ = (
        sa.Index("ix_research_tasks_job_id", "job_id"),
        sa.Index("ix_research_tasks_status", "status"),
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
    # Ordinal within job (0-based)
    task_index: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    status: Mapped[ResearchTaskStatus] = mapped_column(
        sa.Enum(ResearchTaskStatus, native_enum=True),
        nullable=False,
        default=ResearchTaskStatus.pending,
    )
    # Idempotency key
    task_key: Mapped[str | None] = mapped_column(
        sa.String(512),
        nullable=True,
        unique=True,
    )
    # Task type — e.g., "search", "extract", "synthesize"
    task_type: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    # Depth within task graph
    depth: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    # Retry tracking
    retry_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=3)
    # Input/output blobs
    input_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    output_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Error details
    error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # Token accounting
    tokens_input: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    tokens_output: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    # Governance verdict
    governance_verdict: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Advisory approval reference — no FK
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    # Lifecycle timestamps
    started_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
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
