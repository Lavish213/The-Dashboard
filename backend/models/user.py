import datetime
import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base
from models.base import TimestampMixin
from models.enums import UserRole, UserStatus

if TYPE_CHECKING:
    from models.lead import Lead
    from models.notification import Notification
    from models.realtime_session import RealtimeSession


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        unique=True,
        index=True,
    )
    hashed_password: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    full_name: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    role: Mapped[UserRole] = mapped_column(
        sa.Enum(UserRole, native_enum=True),
        nullable=False,
        default=UserRole.operator,
    )
    status: Mapped[UserStatus] = mapped_column(
        sa.Enum(UserStatus, native_enum=True),
        nullable=False,
        default=UserStatus.active,
    )
    last_active_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    leads: Mapped[list["Lead"]] = relationship(
        "Lead",
        back_populates="assigned_user",
        foreign_keys="Lead.assigned_user_id",
    )
    realtime_sessions: Mapped[list["RealtimeSession"]] = relationship(
        "RealtimeSession",
        back_populates="user",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
    )
