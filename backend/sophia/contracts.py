"""
Sophia contracts — immutable input/output types for Phase 12.
All dataclasses are frozen. No mutable state crosses Sophia runtime boundaries.
Provider-agnostic: same contracts for text, voice, and future phone channels.

Extended with:
  - TurnSignals: live per-session confidence/trust/deal_heat computation
  - ContextPacket: seller summary packet delivered on warm transfer
  - TransferReason: enum of handoff trigger reasons
  - HandoffPayload: full transfer initiation payload
  - SophiaSessionMode: AI vs HUMAN_TAKEOVER mode
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID

from models.enums import (
    SophiaChannelType,
    SophiaHandoffStatus,
    SophiaInterruptionReason,
    SophiaSessionStatus,
    SophiaTurnStatus,
)


class TransferReason(str, Enum):
    trust_low = "trust_low"
    hot_lead = "hot_lead"
    seller_requested = "seller_requested"
    ai_uncertain = "ai_uncertain"
    negotiation = "negotiation"
    legal_concern = "legal_concern"
    operator_manual = "operator_manual"


@dataclass(frozen=True)
class TurnSignals:
    """Live per-session signal computation from turn history."""
    confidence_score: float
    trust_score: float
    deal_heat: float
    handoff_recommended: bool
    signal_notes: list[str]


@dataclass(frozen=True)
class ContextPacket:
    """
    Seller summary packet built on warm transfer.
    Delivered to the human operator the moment they join the call.
    """
    session_id: UUID
    lead_id: UUID | None
    seller_name: str | None
    address: str | None
    phone: str | None
    motivation: str | None
    timeline: str | None
    emotional_state: str | None
    deal_heat: float
    trust_score: float
    confidence_score: float
    transfer_reason: TransferReason
    objections_raised: list[str]
    key_moments: list[str]
    sophia_summary: str
    turn_count: int
    tokens_used: int
    built_at: datetime


@dataclass(frozen=True)
class HandoffPayload:
    """Full payload for initiating a warm transfer."""
    session_id: UUID
    transfer_reason: TransferReason
    context_packet: ContextPacket
    initiated_by: UUID | None
    operator_user_id: UUID | None
    initiated_at: datetime


@dataclass(frozen=True)
class SophiaSessionSpec:
    """Input for creating a new Sophia session."""
    session_key: str
    channel: SophiaChannelType
    token_budget: int = 8192
    max_turns: int = 50
    workflow_id: UUID | None = None
    lead_id: UUID | None = None
    initiated_by: UUID | None = None
    channel_metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SophiaSessionRecord:
    """Immutable snapshot of a Sophia session state."""
    session_id: UUID
    session_key: str
    status: SophiaSessionStatus
    channel: SophiaChannelType
    workflow_id: UUID | None
    lead_id: UUID | None
    initiated_by: UUID | None
    token_budget: int
    tokens_used: int
    turn_count: int
    max_turns: int
    channel_metadata: dict
    checkpoint_state: dict | None
    created_at: datetime
    handoff_to: UUID | None = None
    handoff_reason: str | None = None
    mode: str = "ai"
    taken_over_at: datetime | None = None
    taken_over_by: UUID | None = None


@dataclass(frozen=True)
class SophiaTurnInput:
    """Input for starting a new conversation turn."""
    session_id: UUID
    turn_index: int
    input_payload: dict
    turn_key: str | None = None
    actor_id: UUID | None = None


@dataclass(frozen=True)
class SophiaTurnRecord:
    """Immutable snapshot of a turn state."""
    turn_id: UUID
    session_id: UUID
    turn_index: int
    status: SophiaTurnStatus
    input_payload: dict
    output_payload: dict | None
    tool_calls: list
    governance_verdict: dict | None
    tokens_input: int
    tokens_output: int
    interruption_reason: SophiaInterruptionReason | None
    interruption_notes: str | None
    approval_id: UUID | None
    created_at: datetime
    confidence_delta: float = 0.0
    emotional_signal: str | None = None
    handoff_recommended: bool = False


@dataclass(frozen=True)
class SophiaInterruption:
    """Signal that a turn was interrupted."""
    session_id: UUID
    turn_id: UUID
    reason: SophiaInterruptionReason
    notes: str | None = None
    actor_id: UUID | None = None


@dataclass(frozen=True)
class SophiaHandoffRequest:
    """Request to hand off a session to a human operator."""
    session_id: UUID
    handoff_to: UUID
    reason: str
    requested_by: UUID | None = None


@dataclass(frozen=True)
class SophiaHandoffRecord:
    """State of a handoff request."""
    session_id: UUID
    handoff_to: UUID
    reason: str
    status: SophiaHandoffStatus
    requested_at: datetime


@dataclass(frozen=True)
class SophiaToolPermissionRequest:
    """Request to check if a tool is permitted for the current turn."""
    session_id: UUID
    turn_id: UUID
    tool_name: str
    action: str
    risk_tier: str
    actor_id: UUID | None = None
    context: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SophiaToolPermissionResult:
    """Result of tool permission check."""
    tool_name: str
    action: str
    permitted: bool
    requires_approval: bool
    approval_id: UUID | None
    classification: str
    reason: str | None = None


@dataclass(frozen=True)
class SophiaCheckpoint:
    """Point-in-time checkpoint for resumable replay."""
    checkpoint_id: str
    session_id: UUID
    turn_index: int
    token_budget_remaining: int
    state_blob: dict
    captured_at: datetime


@dataclass(frozen=True)
class SophiaCancellationRequest:
    """Request to cancel a session or turn."""
    session_id: UUID
    reason: str
    turn_id: UUID | None = None
    actor_id: UUID | None = None


@dataclass(frozen=True)
class SophiaMetrics:
    """Aggregated Sophia metrics over a time period."""
    total_sessions: int
    sessions_completed: int
    sessions_cancelled: int
    sessions_handed_off: int
    sessions_failed: int
    total_turns: int
    turns_interrupted: int
    tool_permission_checks: int
    tool_blocks: int
    governance_gates_triggered: int
    period_start: datetime
    period_end: datetime


@dataclass(frozen=True)
class SophiaReplayFrame:
    """One frame in a deterministic conversation replay."""
    frame_index: int
    event_type: str
    session_id: UUID
    turn_id: UUID | None
    payload: dict
    emitted_at: datetime


@dataclass(frozen=True)
class SophiaContextInput:
    """Input spec for assembling context for a Sophia turn."""
    session_id: UUID
    turn_index: int
    token_budget: int
    workflow_id: UUID | None = None
    transcript_id: UUID | None = None
    execution_id: UUID | None = None


@dataclass(frozen=True)
class SophiaProviderBoundary:
    """Provider-agnostic boundary spec for voice/text channels."""
    channel: SophiaChannelType
    provider_name: str
    supports_interruption: bool
    supports_barge_in: bool
    max_utterance_tokens: int
    metadata: dict = field(default_factory=dict)