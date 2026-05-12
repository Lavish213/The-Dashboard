import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base
from models.enums import TranscriptStreamType

if TYPE_CHECKING:
    from models.transcript import Transcript


class TranscriptChunk(Base):
    """Append-only ordered chunk of transcript text."""
    __tablename__ = "transcript_chunks"

    __table_args__ = (
        # Primary ordering index
        sa.Index("ix_transcript_chunks_transcript_id_chunk_index", "transcript_id", "chunk_index"),
        # Prevent duplicate chunk_index per transcript
        sa.UniqueConstraint("transcript_id", "chunk_index", name="uq_transcript_chunks_position"),
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
    )
    chunk_index: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
    )
    speaker: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
    )
    text: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    stream_type: Mapped[TranscriptStreamType] = mapped_column(
        sa.Enum(TranscriptStreamType, native_enum=True),
        nullable=False,
        default=TranscriptStreamType.user,
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("clock_timestamp()"),
        nullable=False,
    )

    # Relationships
    transcript: Mapped["Transcript"] = relationship(
        "Transcript",
        back_populates="chunks",
    )
