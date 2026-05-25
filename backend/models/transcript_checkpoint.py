"""
TranscriptCheckpoint — append-only resume markers for transcript streams.

A checkpoint records the position (chunk_index) at which a stream can
be safely resumed after interruption. Multiple checkpoints may exist per
transcript/stream; callers always resume from the latest.

Idempotent: (transcript_id, chunk_index) is unique — re-checkpointing at
the same position is a no-op.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base


class TranscriptCheckpoint(Base):
    __tablename__ = "transcript_checkpoints"

    __table_args__ = (
        sa.UniqueConstraint(
            "transcript_id",
            "chunk_index",
            name="uq_transcript_checkpoints_position",
        ),
        sa.Index("ix_transcript_checkpoints_transcript_id", "transcript_id"),
        sa.Index("ix_transcript_checkpoints_stream_id", "stream_id"),
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
    # Optional stream linkage
    stream_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    # Position: resume from chunks after this index
    chunk_index: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
    )
    # Arbitrary resume state — e.g. {"conversation_context": [...]}
    state: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    # Human-readable label, e.g. "after_intro", "reconnect_1"
    label: Mapped[str | None] = mapped_column(
        sa.String(256),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        nullable=False,
    )
