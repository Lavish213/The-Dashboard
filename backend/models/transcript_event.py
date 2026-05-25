import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from models.transcript import Transcript


class TranscriptEvent(Base):
    """Append-only event log for transcript lifecycle transitions."""
    __tablename__ = "transcript_events"

    __table_args__ = (
        # Primary replay ordering index
        sa.Index("ix_transcript_events_transcript_id_sequence", "transcript_id", "sequence"),
        sa.Index("ix_transcript_events_event_type", "event_type"),
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
    event_type: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(
        sa.JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("clock_timestamp()"),
        nullable=False,
    )

    # Relationships
    transcript: Mapped["Transcript"] = relationship(
        "Transcript",
        back_populates="events",
    )
