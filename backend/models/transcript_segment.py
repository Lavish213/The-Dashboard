import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from db.base import Base

if TYPE_CHECKING:
    from models.transcript import Transcript


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    __table_args__ = (
        sa.Index("ix_transcript_segments_transcript_id_start_ms", "transcript_id", "start_ms"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    transcript_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("transcripts.id"),
        nullable=False,
        index=True,
    )
    speaker: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    start_ms: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        index=True,
    )
    end_ms: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
    )
    sentiment: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    emotion: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    sequence_number: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata_",
        sa.JSON,
        nullable=False,
        default=dict,
    )

    # Relationships
    transcript: Mapped["Transcript"] = relationship(
        "Transcript",
        back_populates="segments",
    )
