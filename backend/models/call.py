import datetime
import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base
from models.base import TimestampMixin
from models.enums import CallProvider, CallStatus

if TYPE_CHECKING:
    from models.lead import Lead
    from models.transcript import Transcript
    from models.workflow import Workflow


class Call(Base, TimestampMixin):
    __tablename__ = "calls"

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
    provider: Mapped[CallProvider] = mapped_column(
        sa.Enum(CallProvider, native_enum=True),
        nullable=False,
        default=CallProvider.twilio,
    )
    call_status: Mapped[CallStatus] = mapped_column(
        sa.Enum(CallStatus, native_enum=True),
        nullable=False,
        default=CallStatus.initiated,
        index=True,
    )
    provider_call_id: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    duration_seconds: Mapped[int | None] = mapped_column(
        sa.Integer,
        nullable=True,
    )
    recording_url: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )

    # Relationships
    lead: Mapped["Lead | None"] = relationship(
        "Lead",
        back_populates="calls",
    )
    workflow: Mapped["Workflow | None"] = relationship(
        "Workflow",
        back_populates="calls",
    )
    transcripts: Mapped[list["Transcript"]] = relationship(
        "Transcript",
        back_populates="call",
    )
