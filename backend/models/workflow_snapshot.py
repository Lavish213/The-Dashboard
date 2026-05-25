"""
WorkflowSnapshot — point-in-time full state capture for forensics and restore.

Distinct from WorkflowCheckpoint (step-level) — captures complete serialized
workflow state including approval summary and lease status.
Append-only: each take() creates a new row. Never mutated after insert.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class WorkflowSnapshot(Base):
    __tablename__ = "workflow_snapshots"

    __table_args__ = (
        sa.Index("ix_workflow_snapshots_workflow_id", "workflow_id"),
        sa.Index("ix_workflow_snapshots_captured_at", "captured_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Redundant fields for fast queries without deserializing state
    workflow_status: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    current_step: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    # Full JSONB state blob
    state: Mapped[dict] = mapped_column(sa.JSON, nullable=False, default=dict)
    captured_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("clock_timestamp()"),
    )
    trigger: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
