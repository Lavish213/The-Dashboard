"""
WorkflowLease — execution lease for distributed workflow coordination.

One lease per workflow (unique on workflow_id). lease_id rotates on each
acquisition so stale holders can be detected.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from models.enums import LeaseStatus


class WorkflowLease(Base):
    __tablename__ = "workflow_leases"
    __table_args__ = (
        sa.Index("ix_workflow_leases_expires_at", "expires_at"),
        sa.Index("ix_workflow_leases_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    lease_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), nullable=False, default=uuid.uuid4
    )
    holder: Mapped[str] = mapped_column(sa.String(256), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("clock_timestamp()"),
    )
    expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    renewed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    released_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    status: Mapped[LeaseStatus] = mapped_column(
        sa.Enum(LeaseStatus, native_enum=True),
        nullable=False,
        default=LeaseStatus.active,
    )
