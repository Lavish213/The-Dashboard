"""
ContextSnapshot — persisted assembled context for replay-safe reconstruction.

One snapshot captures the full assembled context at a point in time.
Snapshots are immutable after creation. Assembly inputs are stored as
provenance metadata for forensic reconstruction.

assembly_key: caller-supplied idempotency key (unique per snapshot).
layer_types: JSON array of ContextLayerType values included.
token_count: total tokens in the assembled context window.
provenance: JSON blob with source attribution per layer.
window_payload: the assembled context items as a JSON payload.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base
from models.enums import ContextSnapshotStatus


class ContextSnapshot(Base):
    __tablename__ = "context_snapshots"

    __table_args__ = (
        sa.Index("ix_context_snapshots_workflow_id", "workflow_id"),
        sa.Index("ix_context_snapshots_status", "status"),
        sa.Index("ix_context_snapshots_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Caller-supplied idempotency key — unique per snapshot
    assembly_key: Mapped[str] = mapped_column(
        sa.String(512),
        nullable=False,
        unique=True,
    )
    status: Mapped[ContextSnapshotStatus] = mapped_column(
        sa.Enum(ContextSnapshotStatus, native_enum=True),
        nullable=False,
        default=ContextSnapshotStatus.active,
    )
    # Optional linkage — advisory, no FK constraints
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    transcript_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    execution_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    # Token counts
    token_count: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
    )
    token_budget: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
    )
    # Layer types included — JSON array of ContextLayerType values
    layer_types: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    # Full assembled context items payload
    window_payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    # Source attribution per layer
    provenance: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    # Assembly parameters used (strategy, truncation policy, etc.)
    assembly_params: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
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
