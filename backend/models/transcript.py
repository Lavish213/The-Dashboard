import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from models.base import TimestampMixin
from models.enums import TranscriptSourceType, TranscriptStatus

if TYPE_CHECKING:
    from models.call import Call
    from models.lead import Lead
    from models.transcript_chunk import TranscriptChunk
    from models.transcript_event import TranscriptEvent
    from models.transcript_segment import TranscriptSegment
    from models.workflow import Workflow


class Transcript(Base, TimestampMixin):
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("leads.id"),
        nullable=True,
        index=True,
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("workflows.id"),
        nullable=True,
        index=True,
    )
    call_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("calls.id"),
        nullable=True,
        index=True,
    )
    transcript_status: Mapped[TranscriptStatus] = mapped_column(
        sa.Enum(TranscriptStatus, native_enum=True),
        nullable=False,
        default=TranscriptStatus.created,
        index=True,
    )
    source_type: Mapped[TranscriptSourceType] = mapped_column(
        sa.Enum(TranscriptSourceType, native_enum=True),
        nullable=False,
        default=TranscriptSourceType.call,
    )
    duration_seconds: Mapped[int | None] = mapped_column(
        sa.Integer,
        nullable=True,
    )

    # Relationships
    lead: Mapped["Lead | None"] = relationship(
        "Lead",
        back_populates="transcripts",
    )
    workflow: Mapped["Workflow | None"] = relationship(
        "Workflow",
        back_populates="transcripts",
    )
    call: Mapped["Call | None"] = relationship(
        "Call",
        back_populates="transcripts",
    )
    segments: Mapped[list["TranscriptSegment"]] = relationship(
        "TranscriptSegment",
        back_populates="transcript",
    )
    chunks: Mapped[list["TranscriptChunk"]] = relationship(
        "TranscriptChunk",
        back_populates="transcript",
    )
    events: Mapped[list["TranscriptEvent"]] = relationship(
        "TranscriptEvent",
        back_populates="transcript",
    )
