"""
SophiaTurn — one conversation turn within a SophiaSession.
A turn begins when Sophia starts generating a response and ends when
the response is complete, interrupted, or cancelled. Holds input/output
blobs, token counts, tool calls attempted, and governance verdict.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base
from models.enums import SophiaInterruptionReason, SophiaTurnStatus


class SophiaTurn(Base):
    __tablename__ = "sophia_turns"
    __table_args__ = (
        sa.Index("ix_sophia_turns_session_id", "session_id"),
        sa.Index("ix_sophia_turns_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("sophia_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_index: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    status: Mapped[SophiaTurnStatus] = mapped_column(
        sa.Enum(SophiaTurnStatus, native_enum=True),
        nullable=False,
        default=SophiaTurnStatus.pending,
    )
    turn_key: Mapped[str | None] = mapped_column(
        sa.String(512), nullable=True, unique=True,
    )
    input_payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
    )
    output_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tool_calls: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list,
    )
    governance_verdict: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tokens_input: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    tokens_output: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    interruption_reason: Mapped[SophiaInterruptionReason | None] = mapped_column(
        sa.Enum(SophiaInterruptionReason, native_enum=True), nullable=True,
    )
    interruption_notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), nullable=True,
    )
    confidence_delta: Mapped[float] = mapped_column(
        sa.Float, nullable=False, default=0.0,
    )
    emotional_signal: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    handoff_recommended: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False,
    )
    error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
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