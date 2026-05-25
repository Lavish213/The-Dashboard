"""
GovernancePolicy — versioned policy record.

Each policy is identified by (policy_key, version). When a policy is
superseded, old row status → superseded; new row is inserted at version+1.
action_patterns: JSON list of fnmatch patterns (e.g. "workflow.*", "ai.tool.*").
rules: arbitrary JSONB blob for policy-specific logic.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base
from models.enums import (
    ActionClassification,
    ApprovalRoutingStrategy,
    GovernancePolicyStatus,
    RiskTier,
)


class GovernancePolicy(Base):
    __tablename__ = "governance_policies"

    __table_args__ = (
        sa.UniqueConstraint("policy_key", "version", name="uq_governance_policies_key_version"),
        sa.Index("ix_governance_policies_status", "status"),
        sa.Index("ix_governance_policies_risk_tier", "risk_tier"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Logical identity — same key, multiple versions
    policy_key: Mapped[str] = mapped_column(
        sa.String(256),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=1,
    )
    status: Mapped[GovernancePolicyStatus] = mapped_column(
        sa.Enum(GovernancePolicyStatus, native_enum=True),
        nullable=False,
        default=GovernancePolicyStatus.active,
    )
    description: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )
    # fnmatch patterns for actions this policy governs
    action_patterns: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    classification: Mapped[ActionClassification] = mapped_column(
        sa.Enum(ActionClassification, native_enum=True),
        nullable=False,
        default=ActionClassification.safe,
    )
    risk_tier: Mapped[RiskTier] = mapped_column(
        sa.Enum(RiskTier, native_enum=True),
        nullable=False,
        default=RiskTier.standard,
    )
    routing_strategy: Mapped[ApprovalRoutingStrategy] = mapped_column(
        sa.Enum(ApprovalRoutingStrategy, native_enum=True),
        nullable=False,
        default=ApprovalRoutingStrategy.direct,
    )
    # JSON list of UUID strings — direct approver IDs
    approver_ids: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    # JSON list of {escalate_to: UUID, after_seconds: int, reason?: str}
    escalation_chain: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    # 0 = no quorum; N = N approvals required
    quorum_required: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
    )
    # Approval timeout in seconds (default 24h)
    timeout_seconds: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=86400,
    )
    # Escalation step timeout in seconds
    escalation_timeout_seconds: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=3600,
    )
    # Parent policy_key for inheritance (advisory)
    inherited_from: Mapped[str | None] = mapped_column(
        sa.String(256),
        nullable=True,
    )
    # Arbitrary policy-specific rules
    rules: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    # Actor who created this policy version
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
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
