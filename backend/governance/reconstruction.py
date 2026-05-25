"""
ApprovalHistoryReconstructor — deterministic approval history replay.

reconstruct(approval_id) — return ordered list of governance events
  for an approval, with interpreted state transitions.

This is read-only forensic reconstruction — no DB writes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import ApprovalStatus, GovernanceEventType
from repositories.approval import ApprovalRepository
from repositories.governance_event import GovernanceEventRepository


@dataclass(frozen=True)
class ApprovalHistoryEntry:
    """One event in the approval history timeline."""

    event_id: UUID
    event_type: GovernanceEventType
    payload: dict
    actor_id: UUID | None
    occurred_at: datetime
    interpreted_state: str


@dataclass(frozen=True)
class ApprovalHistory:
    """Full history of an approval from creation to resolution."""

    approval_id: UUID
    current_status: ApprovalStatus
    entries: tuple[ApprovalHistoryEntry, ...]
    escalation_depth: int
    quorum_votes: int
    override_applied: bool
    fully_reconstructed: bool


class ApprovalHistoryReconstructor:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = GovernanceEventRepository(session)
        self._approvals = ApprovalRepository(session)

    async def reconstruct(self, approval_id: UUID) -> ApprovalHistory | None:
        """
        Reconstruct approval history from governance_events.
        Returns None if approval not found.
        """
        approval = await self._approvals.get_by_id(approval_id)
        if approval is None:
            return None

        events = await self._events.get_for_approval(approval_id)

        entries = []
        escalation_depth = 0
        quorum_votes = 0
        override_applied = False

        for evt in events:
            state = self._interpret_state(evt.event_type)

            if evt.event_type == GovernanceEventType.escalation_triggered:
                escalation_depth += 1
            elif evt.event_type == GovernanceEventType.quorum_vote_cast:
                quorum_votes += 1
            elif evt.event_type == GovernanceEventType.override_applied:
                override_applied = True

            entries.append(
                ApprovalHistoryEntry(
                    event_id=evt.id,
                    event_type=evt.event_type,
                    payload=evt.payload,
                    actor_id=evt.actor_id,
                    occurred_at=evt.created_at,
                    interpreted_state=state,
                )
            )

        return ApprovalHistory(
            approval_id=approval_id,
            current_status=approval.approval_status,
            entries=tuple(entries),
            escalation_depth=escalation_depth,
            quorum_votes=quorum_votes,
            override_applied=override_applied,
            fully_reconstructed=True,
        )

    def _interpret_state(self, event_type: GovernanceEventType) -> str:
        _map = {
            GovernanceEventType.approval_routed: "routed",
            GovernanceEventType.escalation_triggered: "escalated",
            GovernanceEventType.escalation_resolved: "escalation_resolved",
            GovernanceEventType.quorum_vote_cast: "vote_cast",
            GovernanceEventType.quorum_met: "quorum_met",
            GovernanceEventType.override_applied: "override_applied",
            GovernanceEventType.policy_evaluated: "evaluated",
        }
        return _map.get(event_type, event_type.value)
