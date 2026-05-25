"""
SophiaShadowLogger — logs human operator behavior post-takeover.

When your mom takes over a call, this logger watches silently and records:
  - pacing between responses
  - objection handling patterns
  - pivot moments (when she changes topic/approach)
  - close signals (appointment set, price discussed, next steps)
  - call duration post-takeover

This data feeds back into Sophia's prompt calibration over time.
NOT for cloning — for behavioral alignment.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import SophiaEventType
from repositories.sophia_event import SophiaEventRepository


class SophiaShadowLogger:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = SophiaEventRepository(session)

    async def log_human_turn(
        self,
        session_id: UUID,
        turn_index: int,
        speaker: str,
        utterance: str,
        response_time_ms: int | None = None,
        actor_id: UUID | None = None,
    ) -> None:
        """
        Log a single human turn post-takeover.
        Captures pacing and content for calibration.
        """
        await self._events.append(
            SophiaEventType.session_started,
            session_id=session_id,
            actor_id=actor_id,
            payload={
                "shadow_event": "human_turn",
                "turn_index": turn_index,
                "speaker": speaker,
                "utterance_length": len(utterance),
                "response_time_ms": response_time_ms,
                "recorded_at": datetime.now(UTC).isoformat(),
            },
        )

    async def log_objection_handled(
        self,
        session_id: UUID,
        objection: str,
        response_summary: str,
        outcome: str,
        actor_id: UUID | None = None,
    ) -> None:
        """
        Log how your mom handled a specific objection.
        outcome: 'resolved' | 'deflected' | 'unresolved'
        """
        await self._events.append(
            SophiaEventType.session_started,
            session_id=session_id,
            actor_id=actor_id,
            payload={
                "shadow_event": "objection_handled",
                "objection": objection,
                "response_summary": response_summary,
                "outcome": outcome,
                "recorded_at": datetime.now(UTC).isoformat(),
            },
        )

    async def log_close_signal(
        self,
        session_id: UUID,
        signal_type: str,
        details: dict,
        actor_id: UUID | None = None,
    ) -> None:
        """
        Log a close signal detected during human call.
        signal_type: 'appointment_set' | 'price_discussed' | 'next_steps' | 'follow_up_scheduled'
        """
        await self._events.append(
            SophiaEventType.session_completed,
            session_id=session_id,
            actor_id=actor_id,
            payload={
                "shadow_event": "close_signal",
                "signal_type": signal_type,
                "details": details,
                "recorded_at": datetime.now(UTC).isoformat(),
            },
        )

    async def log_pivot(
        self,
        session_id: UUID,
        from_topic: str,
        to_topic: str,
        trigger: str,
        actor_id: UUID | None = None,
    ) -> None:
        """
        Log a topic pivot during human call.
        Captures when and why your mom changes approach.
        """
        await self._events.append(
            SophiaEventType.session_started,
            session_id=session_id,
            actor_id=actor_id,
            payload={
                "shadow_event": "pivot",
                "from_topic": from_topic,
                "to_topic": to_topic,
                "trigger": trigger,
                "recorded_at": datetime.now(UTC).isoformat(),
            },
        )

    async def log_takeover_outcome(
        self,
        session_id: UUID,
        outcome: str,
        duration_seconds: int,
        appointment_set: bool,
        notes: str | None = None,
        actor_id: UUID | None = None,
    ) -> None:
        """
        Log the final outcome of a human-handled call.
        outcome: 'appointment_set' | 'callback_scheduled' | 'not_interested' | 'needs_followup'
        """
        await self._events.append(
            SophiaEventType.session_completed,
            session_id=session_id,
            actor_id=actor_id,
            payload={
                "shadow_event": "takeover_outcome",
                "outcome": outcome,
                "duration_seconds": duration_seconds,
                "appointment_set": appointment_set,
                "notes": notes,
                "recorded_at": datetime.now(UTC).isoformat(),
            },
        )