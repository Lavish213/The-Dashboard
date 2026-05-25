"""
GovernanceEvent — append-only governance event log.

All governance runtime transitions emit a GovernanceEvent.
Rows are immutable after creation. Never updated or deleted.

policy_id / approval_id: advisory references — no FK constraints.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base
from models.enums import GovernanceEventType


class GovernanceEvent(Base):
    __tablename__ = "governance_events"

    __table_args__ = (
        sa.Index("ix_governance_events_approval_id", "approval_id"),
        sa.Index("ix_governance_events_policy_id", "policy_id"),
        sa.Index("ix_governance_events_event_type", "event_type"),
        sa.Index("ix_governance_events_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    event_type: Mapped[GovernanceEventType] = mapped_column(
        sa.Enum(GovernanceEventType, native_enum=True),
        nullable=False,
    )
    # Advisory linkage — no FK constraints
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        nullable=False,
    )
