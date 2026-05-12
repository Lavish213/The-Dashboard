import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from db.session import Base
from models.base import TimestampMixin
from models.enums import RealtimeSessionStatus

if TYPE_CHECKING:
    from models.user import User


class RealtimeSession(Base, TimestampMixin):
    __tablename__ = "realtime_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    socket_id: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
    )
    session_status: Mapped[RealtimeSessionStatus] = mapped_column(
        sa.Enum(RealtimeSessionStatus, native_enum=True),
        nullable=False,
        default=RealtimeSessionStatus.connected,
        index=True,
    )
    connected_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )
    disconnected_at: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    last_heartbeat_at: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    device_info: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="realtime_sessions",
    )
