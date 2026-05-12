"""CallSession — realtime call session record. Separate from Call (business entity)."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base
from models.base import TimestampMixin
from models.enums import CallSessionStatus

if TYPE_CHECKING:
    from models.call import Call
    from models.call_event import CallEvent
    from models.call_participant import CallParticipant


class CallSession(Base, TimestampMixin):
    __tablename__ = "call_sessions"

    __table_args__ = (
        sa.Index("ix_call_sessions_status", "session_status"),
        sa.Index("ix_call_sessions_call_id", "call_id"),
        sa.Index("ix_call_sessions_correlation_id", "correlation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    call_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("calls.id"),
        nullable=True,
    )
    session_status: Mapped[CallSessionStatus] = mapped_column(
        sa.Enum(CallSessionStatus, native_enum=True),
        nullable=False,
        default=CallSessionStatus.waiting,
    )
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=False,
        default=uuid.uuid4,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    call: Mapped["Call | None"] = relationship("Call", foreign_keys=[call_id])
    participants: Mapped[list["CallParticipant"]] = relationship(
        "CallParticipant",
        back_populates="session",
        lazy="noload",
    )
    events: Mapped[list["CallEvent"]] = relationship(
        "CallEvent",
        back_populates="session",
        lazy="noload",
    )
