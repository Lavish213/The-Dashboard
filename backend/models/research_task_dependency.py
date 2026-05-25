"""
ResearchTaskDependency — directed edge in a research task DAG.

upstream_task_id must complete before downstream_task_id may run.
job_id is denormalized for fast per-job queries.
Unique constraint prevents duplicate edges.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base


class ResearchTaskDependency(Base):
    __tablename__ = "research_task_dependencies"

    __table_args__ = (
        sa.UniqueConstraint(
            "upstream_task_id",
            "downstream_task_id",
            name="uq_research_task_dep",
        ),
        sa.Index("ix_research_task_dep_job_id", "job_id"),
        sa.Index("ix_research_task_dep_downstream", "downstream_task_id"),
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
    upstream_task_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("research_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    downstream_task_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("research_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        nullable=False,
    )
