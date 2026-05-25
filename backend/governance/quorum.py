"""
QuorumRuntime — multi-approver quorum support.

cast_vote(approval_id, voter_id, vote, notes) — record one vote.
get_result(approval_id, required) — compute current quorum state.
is_met(approval_id, required) — quick quorum check.

Votes are stored as governance_events (quorum_vote_cast, quorum_met).
Each voter may only vote once per approval — duplicate votes raise QuorumError.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from governance.contracts import QuorumResult, QuorumVote
from models.enums import GovernanceEventType
from repositories.governance_event import GovernanceEventRepository


class QuorumError(Exception):
    pass


class QuorumRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = GovernanceEventRepository(session)

    async def cast_vote(
        self,
        approval_id: UUID,
        voter_id: UUID,
        vote: bool,
        required: int,
        notes: str | None = None,
    ) -> QuorumResult:
        """
        Record one vote for approval_id.
        Raises QuorumError if voter has already voted or if quorum already met.

        Returns updated QuorumResult after the vote.
        """
        events = await self._events.get_for_approval(approval_id)

        # Check quorum not already met
        for evt in events:
            if evt.event_type == GovernanceEventType.quorum_met:
                raise QuorumError(f"Quorum already met for approval {approval_id}")

        # Check voter hasn't already voted
        for evt in events:
            if evt.event_type == GovernanceEventType.quorum_vote_cast:
                if evt.payload.get("voter_id") == str(voter_id):
                    raise QuorumError(
                        f"Voter {voter_id} already cast a vote for approval {approval_id}"
                    )

        await self._events.append(
            event_type=GovernanceEventType.quorum_vote_cast,
            approval_id=approval_id,
            actor_id=voter_id,
            payload={
                "voter_id": str(voter_id),
                "vote": vote,
                "notes": notes,
                "voted_at": datetime.now(UTC).isoformat(),
            },
        )

        result = await self.get_result(approval_id, required)

        if result.quorum_met and not result.resolved:
            await self._events.append(
                event_type=GovernanceEventType.quorum_met,
                approval_id=approval_id,
                actor_id=voter_id,
                payload={
                    "votes_for": result.votes_for,
                    "votes_against": result.votes_against,
                    "required": required,
                },
            )
            return QuorumResult(
                approval_id=result.approval_id,
                required=result.required,
                votes_for=result.votes_for,
                votes_against=result.votes_against,
                quorum_met=True,
                resolved=True,
            )
        return result

    async def get_result(self, approval_id: UUID, required: int) -> QuorumResult:
        """Compute current quorum state from event log."""
        events = await self._events.get_for_approval(approval_id)

        votes_for = 0
        votes_against = 0
        resolved = False

        for evt in events:
            if evt.event_type == GovernanceEventType.quorum_vote_cast:
                if evt.payload.get("vote") is True:
                    votes_for += 1
                else:
                    votes_against += 1
            elif evt.event_type == GovernanceEventType.quorum_met:
                resolved = True

        quorum_met = votes_for >= required

        return QuorumResult(
            approval_id=approval_id,
            required=required,
            votes_for=votes_for,
            votes_against=votes_against,
            quorum_met=quorum_met,
            resolved=resolved,
        )

    def build_vote(
        self,
        approval_id: UUID,
        voter_id: UUID,
        vote: bool,
        notes: str | None = None,
    ) -> QuorumVote:
        """Build a QuorumVote value object (does not persist)."""
        return QuorumVote(
            approval_id=approval_id,
            voter_id=voter_id,
            vote=vote,
            voted_at=datetime.now(UTC),
            notes=notes,
        )
