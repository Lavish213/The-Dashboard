"""
SophiaCheckpointRuntime — Sophia session checkpointing.

Captures full session state as a snapshot blob stored on the session row
and emitted as a SophiaEvent. Enables deterministic replay and resumption.

A checkpoint is taken:
- After each turn completes
- Before handoff
- On explicit checkpoint request

Replay is position-based: checkpoints are ordered by turn_index.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import SophiaEventType
from repositories.sophia_event import SophiaEventRepository
from repositories.sophia_session import SophiaSessionRepository
from sophia.contracts import SophiaCheckpoint


class SophiaCheckpointRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = SophiaSessionRepository(session)
        self._events = SophiaEventRepository(session)

    async def capture(
        self,
        session_id: UUID,
        turn_index: int,
        extra_state: dict | None = None,
    ) -> SophiaCheckpoint:
        """
        Capture current session state as a checkpoint.
        Persists checkpoint_state on session row + emits checkpoint_saved event.
        """
        session_row = await self._sessions.get_for_update(session_id)
        if session_row is None:
            raise ValueError(f"Session {session_id} not found")

        checkpoint_id = str(uuid.uuid4())
        captured_at = datetime.now(UTC)
        token_budget_remaining = session_row.token_budget - session_row.tokens_used

        state_blob = {
            "checkpoint_id": checkpoint_id,
            "turn_index": turn_index,
            "status": session_row.status.value,
            "tokens_used": session_row.tokens_used,
            "token_budget_remaining": token_budget_remaining,
            "turn_count": session_row.turn_count,
            "captured_at": captured_at.isoformat(),
            **(extra_state or {}),
        }

        session_row.checkpoint_state = state_blob
        self._session.add(session_row)
        await self._session.flush()

        await self._events.append(
            SophiaEventType.checkpoint_saved,
            session_id=session_id,
            payload={
                "checkpoint_id": checkpoint_id,
                "turn_index": turn_index,
                "token_budget_remaining": token_budget_remaining,
            },
        )

        return SophiaCheckpoint(
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            turn_index=turn_index,
            token_budget_remaining=token_budget_remaining,
            state_blob=state_blob,
            captured_at=captured_at,
        )

    async def get_latest(self, session_id: UUID) -> SophiaCheckpoint | None:
        """Retrieve the latest checkpoint from the session row."""
        session_row = await self._sessions.get(session_id)
        if session_row is None or session_row.checkpoint_state is None:
            return None

        blob = session_row.checkpoint_state
        return SophiaCheckpoint(
            checkpoint_id=blob["checkpoint_id"],
            session_id=session_id,
            turn_index=blob["turn_index"],
            token_budget_remaining=blob["token_budget_remaining"],
            state_blob=blob,
            captured_at=datetime.fromisoformat(blob["captured_at"]),
        )

    async def list_checkpoints(self, session_id: UUID) -> list[SophiaCheckpoint]:
        """
        Reconstruct checkpoint history from checkpoint_saved events.
        Returns ordered list (oldest first).
        """
        events = await self._events.get_by_type(
            SophiaEventType.checkpoint_saved,
            session_id=session_id,
        )
        checkpoints = []
        for event in events:
            p = event.payload
            checkpoints.append(
                SophiaCheckpoint(
                    checkpoint_id=p["checkpoint_id"],
                    session_id=session_id,
                    turn_index=p["turn_index"],
                    token_budget_remaining=p["token_budget_remaining"],
                    state_blob=p,
                    captured_at=event.emitted_at,
                )
            )
        return checkpoints
