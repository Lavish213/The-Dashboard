"""
Governance contracts — immutable input/output types for Phase 11.

All dataclasses are frozen. No mutable state crosses governance boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from models.enums import (
    ActionClassification,
    ApprovalRoutingStrategy,
    ApprovalType,
    GovernancePolicyStatus,
    RiskTier,
)


@dataclass(frozen=True)
class PolicyEvaluationInput:
    """Input to the policy evaluator."""

    action: str                          # e.g. "workflow.offer.create"
    risk_tier: RiskTier
    actor_id: UUID | None = None
    workflow_id: UUID | None = None
    execution_id: UUID | None = None
    context: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyEvaluationResult:
    """Output of deterministic policy evaluation."""

    action: str
    classification: ActionClassification
    risk_tier: RiskTier
    requires_approval: bool
    approval_type: ApprovalType | None
    routing_strategy: ApprovalRoutingStrategy
    approver_ids: tuple[UUID, ...]
    escalation_chain: tuple[EscalationStep, ...]
    quorum_required: int
    timeout_seconds: int
    matched_policy_key: str | None
    matched_policy_version: int
    evaluation_id: str


@dataclass(frozen=True)
class EscalationStep:
    """One step in an escalation chain."""

    escalate_to: UUID
    after_seconds: int
    reason: str | None = None


@dataclass(frozen=True)
class ApprovalRoute:
    """Routing decision for a single approval."""

    approval_id: UUID
    routing_strategy: ApprovalRoutingStrategy
    approver_ids: tuple[UUID, ...]
    escalation_chain: tuple[EscalationStep, ...]
    quorum_required: int
    timeout_seconds: int
    escalation_timeout_seconds: int


@dataclass(frozen=True)
class QuorumVote:
    """One vote cast in a quorum approval."""

    approval_id: UUID
    voter_id: UUID
    vote: bool       # True = approve, False = reject
    voted_at: datetime
    notes: str | None = None


@dataclass(frozen=True)
class QuorumResult:
    """Current quorum state for an approval."""

    approval_id: UUID
    required: int
    votes_for: int
    votes_against: int
    quorum_met: bool
    resolved: bool


@dataclass(frozen=True)
class DelegationGrant:
    """Returned when a delegation is created."""

    delegation_id: UUID
    delegation_key: str
    delegator_id: UUID
    delegate_id: UUID
    approval_types: tuple[str, ...]
    risk_tiers: tuple[str, ...]
    expires_at: datetime | None


@dataclass(frozen=True)
class GovernancePolicySnapshot:
    """Immutable point-in-time policy snapshot for replay."""

    snapshot_id: str
    policy_key: str
    version: int
    status: GovernancePolicyStatus
    classification: ActionClassification
    risk_tier: RiskTier
    action_patterns: tuple[str, ...]
    routing_strategy: ApprovalRoutingStrategy
    approver_ids: tuple[UUID, ...]
    escalation_chain: tuple[EscalationStep, ...]
    quorum_required: int
    timeout_seconds: int
    rules: dict
    inherited_from: str | None
    captured_at: datetime


@dataclass(frozen=True)
class FreezeSpec:
    """Active execution freeze record."""

    freeze_key: str
    scope: str        # "global", "workflow:{uuid}", "execution", etc.
    reason: str
    is_kill_switch: bool
    activated_by: UUID | None
    activated_at: datetime


@dataclass(frozen=True)
class EmergencyOverride:
    """Record of an emergency approval override."""

    override_id: UUID
    override_key: str
    approval_id: UUID
    authorized_by: UUID
    reason: str
    applied_at: datetime


@dataclass(frozen=True)
class GovernanceMetrics:
    """Aggregated governance metrics over a time period."""

    total_evaluations: int
    approvals_pending: int
    approvals_resolved: int
    escalations_triggered: int
    overrides_applied: int
    freeze_events: int
    delegations_active: int
    period_start: datetime
    period_end: datetime
