"""CallParticipant — tracks who is in a call session and their connection state."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from db.base import Base
from models.enums import ParticipantRole, ParticipantStatus

if TYPE_CHECKING:
    from models.call_session import CallSession
    from models.user import User


class CallParticipant(Base):
    __tablename__ = "call_participants"

    __table_args__ = (
        sa.Index("ix_call_participants_session_id", "session_id"),
        sa.Index("ix_call_participants_user_id", "user_id"),
        sa.Index("ix_call_participants_status", "participant_status"),
        sa.Index("ix_call_participants_connection_id", "connection_id"),
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
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id"),
        nullable=True,
    )
    role: Mapped[ParticipantRole] = mapped_column(
        sa.Enum(ParticipantRole, native_enum=True),
        nullable=False,
    )
    participant_status: Mapped[ParticipantStatus] = mapped_column(
        sa.Enum(ParticipantStatus, native_enum=True),
        nullable=False,
        default=ParticipantStatus.joined,
    )
    # WebSocket connection identifier — updated on reconnect
    connection_id: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("clock_timestamp()"),
    )
    left_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    session: Mapped["CallSession"] = relationship(
        "CallSession",
        back_populates="participants",
    )
    user: Mapped["User | None"] = relationship("User", foreign_keys=[user_id])
