"""
DomainEvent — append-only realtime event log.

Indexed for channel-ordered replay. event_id has unique constraint for idempotency.
seq_num is scoped per channel and assigned at write time with an advisory lock.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class DomainEventModel(Base):
    __tablename__ = "domain_events"

    __table_args__ = (
        sa.UniqueConstraint("event_id", name="uq_domain_events_event_id"),
        sa.UniqueConstraint("channel", "seq_num", name="uq_domain_events_channel_seq_num"),
        sa.Index("ix_domain_events_channel_seq_num", "channel", "seq_num"),
        sa.Index("ix_domain_events_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    event_id: Mapped[str] = mapped_column(sa.String, nullable=False)
    channel: Mapped[str] = mapped_column(sa.String, nullable=False)
    seq_num: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    payload: Mapped[dict] = mapped_column(sa.JSON, nullable=False, default=dict)
    correlation_id: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("clock_timestamp()"),
    )
