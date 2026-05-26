from __future__ import annotations

import uuid
import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from models.base import TimestampMixin


class EmailDrip(Base, TimestampMixin):
    __tablename__ = "email_drips"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    email: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    full_name: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    sequence: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        default="nurture",
    )
    step: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
    )
    status: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        default="active",
        index=True,
    )
    next_send_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    last_sent_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    source: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
