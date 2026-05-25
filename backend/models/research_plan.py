"""
ResearchPlan — structured research plan with revision tracking.

Plans are checkpointable and approval-compatible.
Each revision increments the revision counter — old revisions are not deleted.
steps is an ordered list of step descriptor dicts (no schema enforcement here).
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base
from models.enums import ResearchPlanStatus


class ResearchPlan(Base):
    __tablename__ = "research_plans"

    __table_args__ = (
        sa.Index("ix_research_plans_job_id", "job_id"),
        sa.Index("ix_research_plans_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Caller-supplied idempotency key
    plan_key: Mapped[str] = mapped_column(
        sa.String(512),
        nullable=False,
        unique=True,
    )
    # Advisory job reference — no FK
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    status: Mapped[ResearchPlanStatus] = mapped_column(
        sa.Enum(ResearchPlanStatus, native_enum=True),
        nullable=False,
        default=ResearchPlanStatus.draft,
    )
    # Monotonically increasing revision counter
    revision: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    # Human-readable research goal
    goal: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # Ordered list of step descriptors
    steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # Execution constraints (token budget, depth limit, etc.)
    constraints: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Resumable checkpoint blob
    checkpoint_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Advisory approval reference — no FK
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
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
