"""
SophiaMetricsRuntime — Sophia runtime metrics primitives.

Computes metrics via SQL aggregation over sophia_sessions, sophia_turns,
and sophia_events. No in-memory counters — always computed from source of truth.

Extended with per-turn signal computation:
  - confidence_score: 0.0–1.0, how certain Sophia is about the current turn
  - trust_score: 0.0–10.0, seller trust level derived from turn signals
  - deal_heat: 0.0–10.0, composite lead temperature score
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import (
    SophiaEventType,
    SophiaSessionStatus,
    SophiaTurnStatus,
)
from models.sophia_event import SophiaEvent
from models.sophia_session import SophiaSession
from models.sophia_turn import SophiaTurn
from sophia.contracts import SophiaMetrics, TurnSignals


class SophiaMetricsRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def compute(
        self,
        period_start: datetime,
        period_end: datetime,
    ) -> SophiaMetrics:
        async def _count(model, *conditions) -> int:
            result = await self._session.execute(
                select(func.count()).select_from(model).where(*conditions)
            )
            return result.scalar_one() or 0

        total_sessions = await _count(
            SophiaSession,
            SophiaSession.created_at >= period_start,
            SophiaSession.created_at < period_end,
        )
        sessions_completed = await _count(
            SophiaSession,
            SophiaSession.created_at >= period_start,
            SophiaSession.created_at < period_end,
            SophiaSession.status == SophiaSessionStatus.completed,
        )
        sessions_cancelled = await _count(
            SophiaSession,
            SophiaSession.created_at >= period_start,
            SophiaSession.created_at < period_end,
            SophiaSession.status == SophiaSessionStatus.cancelled,
        )
        sessions_handed_off = await _count(
            SophiaSession,
            SophiaSession.created_at >= period_start,
            SophiaSession.created_at < period_end,
            SophiaSession.status == SophiaSessionStatus.handed_off,
        )
        sessions_failed = await _count(
            SophiaSession,
            SophiaSession.created_at >= period_start,
            SophiaSession.created_at < period_end,
            SophiaSession.status == SophiaSessionStatus.failed,
        )
        total_turns = await _count(
            SophiaTurn,
            SophiaTurn.created_at >= period_start,
            SophiaTurn.created_at < period_end,
        )
        turns_interrupted = await _count(
            SophiaTurn,
            SophiaTurn.created_at >= period_start,
            SophiaTurn.created_at < period_end,
            SophiaTurn.status == SophiaTurnStatus.interrupted,
        )
        tool_checks = await _count(
            SophiaEvent,
            SophiaEvent.emitted_at >= period_start,
            SophiaEvent.emitted_at < period_end,
            SophiaEvent.event_type.in_([
                SophiaEventType.tool_permitted,
                SophiaEventType.tool_blocked,
            ]),
        )
        tool_blocks = await _count(
            SophiaEvent,
            SophiaEvent.emitted_at >= period_start,
            SophiaEvent.emitted_at < period_end,
            SophiaEvent.event_type == SophiaEventType.tool_blocked,
        )
        governance_gates = await _count(
            SophiaEvent,
            SophiaEvent.emitted_at >= period_start,
            SophiaEvent.emitted_at < period_end,
            SophiaEvent.event_type == SophiaEventType.governance_evaluated,
        )

        return SophiaMetrics(
            total_sessions=total_sessions,
            sessions_completed=sessions_completed,
            sessions_cancelled=sessions_cancelled,
            sessions_handed_off=sessions_handed_off,
            sessions_failed=sessions_failed,
            total_turns=total_turns,
            turns_interrupted=turns_interrupted,
            tool_permission_checks=tool_checks,
            tool_blocks=tool_blocks,
            governance_gates_triggered=governance_gates,
            period_start=period_start,
            period_end=period_end,
        )

    async def compute_turn_signals(
        self,
        session_id: UUID,
    ) -> TurnSignals:
        """
        Compute live per-session signals from turn history.

        confidence_score: drops when turns are interrupted, looping,
          or awaiting approval repeatedly. starts at 1.0, decays.

        trust_score: 0-10. rises when seller engages, drops on
          objections, interruptions, and repeated misunderstanding.

        deal_heat: 0-10. composite of turn engagement, session
          duration, and absence of disqualifying signals.
        """
        result = await self._session.execute(
            select(SophiaTurn)
            .where(SophiaTurn.session_id == session_id)
            .order_by(SophiaTurn.turn_index)
        )
        turns = result.scalars().all()

        if not turns:
            return TurnSignals(
                confidence_score=1.0,
                trust_score=5.0,
                deal_heat=5.0,
                handoff_recommended=False,
                signal_notes=[],
            )

        total = len(turns)
        interrupted = sum(1 for t in turns if t.status == SophiaTurnStatus.interrupted)
        failed = sum(1 for t in turns if t.status == SophiaTurnStatus.failed)
        approval_gated = sum(1 for t in turns if t.status == SophiaTurnStatus.awaiting_approval)

        interruption_rate = interrupted / total
        failure_rate = failed / total

        confidence_score = max(
            0.0,
            1.0
            - (interruption_rate * 0.4)
            - (failure_rate * 0.5)
            - (approval_gated * 0.05),
        )

        trust_score = min(
            10.0,
            max(
                0.0,
                5.0
                + (total * 0.3)
                - (interrupted * 0.5)
                - (failed * 1.0),
            ),
        )

        deal_heat = min(
            10.0,
            max(
                0.0,
                5.0
                + (total * 0.4)
                - (interrupted * 0.3)
                - (failed * 0.8),
            ),
        )

        handoff_recommended = (
            confidence_score < 0.4
            or trust_score < 3.0
            or interruption_rate > 0.5
        )

        signal_notes: list[str] = []
        if interruption_rate > 0.3:
            signal_notes.append(f"High interruption rate: {interruption_rate:.0%}")
        if confidence_score < 0.4:
            signal_notes.append(f"Low confidence: {confidence_score:.2f}")
        if trust_score < 3.0:
            signal_notes.append(f"Low trust score: {trust_score:.1f}")
        if handoff_recommended:
            signal_notes.append("Handoff recommended")

        return TurnSignals(
            confidence_score=round(confidence_score, 3),
            trust_score=round(trust_score, 2),
            deal_heat=round(deal_heat, 2),
            handoff_recommended=handoff_recommended,
            signal_notes=signal_notes,
        )