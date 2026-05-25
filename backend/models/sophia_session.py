"""
SophiaSession — persistent record of one Sophia conversation session.
Tracks full lifecycle: initializing → active → completed/cancelled/failed/handed_off.
Channel-aware (text/voice/phone). Linked to workflow and lead (advisory, no FK block).
Append-only audit columns; checkpoint_state is resumable blob.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base
from models.enums import SophiaChannelType, SophiaSessionMode, SophiaSessionStatus


class SophiaSession(Base):
    __tablename__ = "sophia_sessions"
    __table_args__ = (
        sa.Index("ix_sophia_sessions_workflow_id", "workflow_id"),
        sa.Index("ix_sophia_sessions_lead_id", "lead_id"),
        sa.Index("ix_sophia_sessions_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    session_key: Mapped[str] = mapped_column(
        sa.String(512), nullable=False, unique=True,
    )
    status: Mapped[SophiaSessionStatus] = mapped_column(
        sa.Enum(SophiaSessionStatus, native_enum=True),
        nullable=False,
        default=SophiaSessionStatus.initializing,
    )
    mode: Mapped[SophiaSessionMode] = mapped_column(
        sa.Enum(SophiaSessionMode, native_enum=True),
        nullable=False,
        default=SophiaSessionMode.ai,
    )
    channel: Mapped[SophiaChannelType] = mapped_column(
        sa.Enum(SophiaChannelType, native_enum=True),
        nullable=False,
        default=SophiaChannelType.text,
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), nullable=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), nullable=True,
    )
    initiated_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    channel_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
    )
    token_budget: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=8192,
    )
    tokens_used: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0,
    )
    turn_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0,
    )
    max_turns: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=50,
    )
    checkpoint_state: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
    )
    cancel_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    handoff_to: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), nullable=True,
    )
    handoff_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    taken_over_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True,
    )
    taken_over_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), nullable=True,
    )
    error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True,
    )
    handed_off_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True,
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