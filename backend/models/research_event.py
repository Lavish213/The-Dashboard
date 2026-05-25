"""
ResearchEvent — append-only audit event log for the research runtime.

All IDs are advisory (no FK constraints) so the event log survives
partial deletions and remains intact for replay.
emitted_at uses clock_timestamp() for monotonic ordering within a transaction.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base
from models.enums import ResearchEventType


class ResearchEvent(Base):
    __tablename__ = "research_events"

    __table_args__ = (
        sa.Index("ix_research_events_job_id", "job_id"),
        sa.Index("ix_research_events_event_type", "event_type"),
        sa.Index("ix_research_events_emitted_at", "emitted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    event_type: Mapped[ResearchEventType] = mapped_column(
        sa.Enum(ResearchEventType, native_enum=True),
        nullable=False,
    )
    # Advisory references — no FK constraints
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
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
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Immutable — set by DB on insert, never updated
    emitted_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        nullable=False,
    )
