"""
SophiaEvent — append-only event log for Sophia session/turn lifecycle.

Never updated after insert. Provides deterministic replay foundation.
All advisory IDs (session_id, turn_id, actor_id) — no FK constraints.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base
from models.enums import SophiaEventType


class SophiaEvent(Base):
    __tablename__ = "sophia_events"

    __table_args__ = (
        sa.Index("ix_sophia_events_session_id", "session_id"),
        sa.Index("ix_sophia_events_turn_id", "turn_id"),
        sa.Index("ix_sophia_events_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    event_type: Mapped[SophiaEventType] = mapped_column(
        sa.Enum(SophiaEventType, native_enum=True),
        nullable=False,
    )
    # Advisory references — no FK constraints (append-only, immutable)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    turn_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    correlation_id: Mapped[str | None] = mapped_column(
        sa.String(256),
        nullable=True,
    )
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    emitted_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        nullable=False,
    )
