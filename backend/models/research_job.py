"""
ResearchJob — top-level research job lifecycle record.

States: queued → running → paused/completed/failed/cancelled
Checkpoint blob enables pause/resume. Token budget enforced by safety runtime.
Advisory links to sophia_session and workflow — no FK block.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base
from models.enums import ResearchJobStatus


class ResearchJob(Base):
    __tablename__ = "research_jobs"

    __table_args__ = (
        sa.Index("ix_research_jobs_status", "status"),
        sa.Index("ix_research_jobs_sophia_session_id", "sophia_session_id"),
        sa.Index("ix_research_jobs_workflow_id", "workflow_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Caller-supplied idempotency key
    job_key: Mapped[str] = mapped_column(
        sa.String(512),
        nullable=False,
        unique=True,
    )
    status: Mapped[ResearchJobStatus] = mapped_column(
        sa.Enum(ResearchJobStatus, native_enum=True),
        nullable=False,
        default=ResearchJobStatus.queued,
    )
    # Advisory linkage — no FK constraints
    sophia_session_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    initiated_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Advisory plan reference
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    # Token accounting
    token_budget: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=16384,
    )
    tokens_used: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
    )
    # Task counters
    task_count: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
    )
    completed_task_count: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
    )
    # Depth guards
    max_depth: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=10,
    )
    current_depth: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
    )
    # Resumable checkpoint blob
    checkpoint_state: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    # Cancellation / error
    cancel_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # Provider-agnostic metadata
    job_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    # Lifecycle timestamps — append-only once set
    started_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    paused_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
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
