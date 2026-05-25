"""
SophiaConfidenceEngine — per-session confidence tracking and handoff triggering.

Reads turn history to compute live signals and determines when
Sophia should recommend a human takeover.

Trigger conditions for HANDOFF_RECOMMENDED:
  - confidence_score < 0.4  (too many failed/interrupted turns)
  - trust_score < 3.0       (seller disengaging)
  - interruption_rate > 0.5 (seller repeatedly cutting off Sophia)
  - seller explicitly requests human
  - consecutive failed turns >= 3
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from sophia.contracts import TransferReason, TurnSignals
from sophia.metrics import SophiaMetricsRuntime


class SophiaConfidenceEngine:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._metrics = SophiaMetricsRuntime(session)

    async def evaluate(self, session_id: UUID) -> TurnSignals:
        """
        Compute current signals for a session.
        Returns TurnSignals with handoff_recommended set if any
        trigger condition is met.
        """
        return await self._metrics.compute_turn_signals(session_id)

    async def get_transfer_reason(self, session_id: UUID) -> TransferReason | None:
        """
        If handoff is recommended, return the primary trigger reason.
        Returns None if no handoff is needed.
        """
        signals = await self.evaluate(session_id)

        if not signals.handoff_recommended:
            return None

        if signals.trust_score < 3.0:
            return TransferReason.trust_low

        if signals.confidence_score < 0.4:
            return TransferReason.ai_uncertain

        notes_lower = " ".join(signals.signal_notes).lower()
        if "interruption" in notes_lower:
            return TransferReason.trust_low

        return TransferReason.ai_uncertain

    async def should_handoff(self, session_id: UUID) -> bool:
        """Simple boolean check — used by interruption runtime."""
        signals = await self.evaluate(session_id)
        return signals.handoff_recommended