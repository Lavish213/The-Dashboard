"""CallEvent — append-only event log for call session lifecycle."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from models.call_session import CallSession


class CallEvent(Base):
    """Append-only. Never mutated after insert. Ordered by (sequence, id) for replay."""
    __tablename__ = "call_events"

    __table_args__ = (
        # Primary replay ordering index
        sa.Index("ix_call_events_session_id_sequence", "session_id", "sequence"),
        sa.Index("ix_call_events_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("call_sessions.id"),
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
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("clock_timestamp()"),
        nullable=False,
    )

    # Relationships
    session: Mapped["CallSession"] = relationship(
        "CallSession",
        back_populates="events",
    )
