"""
ApprovalDelegation — approval authority delegation record.

A delegator grants a delegate the ability to resolve approvals on their behalf.
Scope is narrowed by approval_types and risk_tiers (empty list = all).

delegation_key: caller-supplied idempotency key.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base
from models.enums import DelegationStatus


class ApprovalDelegation(Base):
    __tablename__ = "approval_delegations"

    __table_args__ = (
        sa.Index("ix_approval_delegations_delegator_id", "delegator_id"),
        sa.Index("ix_approval_delegations_delegate_id", "delegate_id"),
        sa.Index("ix_approval_delegations_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Caller-supplied idempotency key
    delegation_key: Mapped[str] = mapped_column(
        sa.String(512),
        nullable=False,
        unique=True,
    )
    delegator_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=False,
    )
    delegate_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=False,
    )
    # JSON list of ApprovalType values — empty = all types
    approval_types: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    # JSON list of RiskTier values — empty = all tiers
    risk_tiers: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    status: Mapped[DelegationStatus] = mapped_column(
        sa.Enum(DelegationStatus, native_enum=True),
        nullable=False,
        default=DelegationStatus.active,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    revoke_reason: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        onupdate=func.clock_timestamp(),
        nullable=False,
    )
