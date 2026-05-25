"""
TranscriptStream — one streaming session within a Transcript.

A Transcript may have multiple streams (e.g., reconnects, retries).
Each stream tracks: lifecycle status, provider, token usage, partial
in-flight text, and last committed chunk index for resume.

partial_text: mutable buffer for the current in-flight fragment.
             Cleared on commit_chunk(). Discarded on interrupt/cancel.
last_chunk_index: index of the last committed TranscriptChunk.
                  Used as resume cursor after interruption.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base
from models.enums import TranscriptStreamStatus


class TranscriptStream(Base):
    __tablename__ = "transcript_streams"

    __table_args__ = (
        sa.Index("ix_transcript_streams_transcript_id", "transcript_id"),
        sa.Index("ix_transcript_streams_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    transcript_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("transcripts.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Caller-supplied idempotency key. Unique per stream.
    stream_key: Mapped[str] = mapped_column(
        sa.String(512),
        nullable=False,
        unique=True,
    )
    status: Mapped[TranscriptStreamStatus] = mapped_column(
        sa.Enum(TranscriptStreamStatus, native_enum=True),
        nullable=False,
        default=TranscriptStreamStatus.pending,
    )
    provider: Mapped[str | None] = mapped_column(
        sa.String(128),
        nullable=True,
    )
    model_name: Mapped[str | None] = mapped_column(
        sa.String(256),
        nullable=True,
    )
    # Token usage — updated on complete or per-chunk commit
    tokens_input: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
    )
    tokens_output: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
    )
    # Mutable buffer: current in-flight partial text (not yet committed as chunk)
    partial_text: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )
    # Resume cursor: index of last successfully committed chunk
    last_chunk_index: Mapped[int | None] = mapped_column(
        sa.Integer,
        nullable=True,
    )
    interruption_reason: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )
    cancel_reason: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(
        sa.Text,
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
    interrupted_at: Mapped[datetime | None] = mapped_column(
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
