"""
WorkflowCheckpoint — append-only step snapshot for deterministic recovery.

One checkpoint per (workflow_id, step) — enforced by unique constraint.
`set_checkpoint` is idempotent: duplicate (workflow, step) pairs are ignored.

Supports:
- rollback-to-step: find last checkpoint before failure
- resume: restore execution context (payload) from checkpoint
- replay validation: compare derived state against checkpoint history
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class WorkflowCheckpoint(Base):
    __tablename__ = "workflow_checkpoints"

    __table_args__ = (
        # One checkpoint per step per workflow — idempotent writes
        sa.UniqueConstraint(
            "workflow_id", "step",
            name="uq_workflow_checkpoints_workflow_step",
        ),
        sa.Index("ix_workflow_checkpoints_workflow_id", "workflow_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("workflows.id"),
        nullable=False,
    )
    step: Mapped[str] = mapped_column(sa.String, nullable=False)
    # String — avoid enum dependency; stores WorkflowStatus value
    status_at_checkpoint: Mapped[str] = mapped_column(sa.String, nullable=False)
    payload: Mapped[dict] = mapped_column(sa.JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("clock_timestamp()"),
    )
