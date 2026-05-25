"""
ContextPacketBuilder — builds the seller summary packet on warm transfer.

Reads from:
  - SophiaSession (session metadata, lead_id, turn_count, tokens_used)
  - SophiaTurn history (objections, emotional signals, key moments)
  - SophiaMetricsRuntime (live trust/confidence/deal_heat signals)
  - Lead model (seller name, address, phone) if lead_id present

The packet is delivered to the human operator the moment they join the call.
They should never join blind.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.sophia_session import SophiaSession
from models.sophia_turn import SophiaTurn
from sophia.contracts import ContextPacket, TransferReason
from sophia.metrics import SophiaMetricsRuntime


class ContextPacketBuilder:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._metrics = SophiaMetricsRuntime(session)

    async def build(
        self,
        session_id: UUID,
        transfer_reason: TransferReason,
    ) -> ContextPacket:
        """
        Build full context packet for a session.
        Safe to call mid-call — reads committed turn history only.
        """
        session_row = await self._session.get(SophiaSession, session_id)
        signals = await self._metrics.compute_turn_signals(session_id)

        turns_result = await self._session.execute(
            select(SophiaTurn)
            .where(SophiaTurn.session_id == session_id)
            .order_by(SophiaTurn.turn_index)
        )
        turns = turns_result.scalars().all()

        seller_name, address, phone = await self._resolve_lead(
            session_row.lead_id if session_row else None
        )

        objections = self._extract_objections(turns)
        key_moments = self._extract_key_moments(turns)
        emotional_state = self._derive_emotional_state(turns, signals)
        motivation = self._derive_motivation(turns)
        timeline = self._extract_timeline(turns)
        summary = self._build_summary(
            seller_name=seller_name,
            signals=signals,
            transfer_reason=transfer_reason,
            turn_count=len(turns),
            objections=objections,
            key_moments=key_moments,
        )

        return ContextPacket(
            session_id=session_id,
            lead_id=session_row.lead_id if session_row else None,
            seller_name=seller_name,
            address=address,
            phone=phone,
            motivation=motivation,
            timeline=timeline,
            emotional_state=emotional_state,
            deal_heat=signals.deal_heat,
            trust_score=signals.trust_score,
            confidence_score=signals.confidence_score,
            transfer_reason=transfer_reason,
            objections_raised=objections,
            key_moments=key_moments,
            sophia_summary=summary,
            turn_count=session_row.turn_count if session_row else len(turns),
            tokens_used=session_row.tokens_used if session_row else 0,
            built_at=datetime.now(UTC),
        )

    async def _resolve_lead(
        self,
        lead_id: UUID | None,
    ) -> tuple[str | None, str | None, str | None]:
        """Resolve seller name, address, phone from lead record."""
        if lead_id is None:
            return None, None, None
        try:
            from models.lead import Lead
            lead = await self._session.get(Lead, lead_id)
            if lead is None:
                return None, None, None
            name = getattr(lead, "seller_name", None) or getattr(lead, "contact_name", None)
            address = getattr(lead, "property_address", None) or getattr(lead, "address", None)
            phone = getattr(lead, "phone", None) or getattr(lead, "contact_phone", None)
            return name, address, phone
        except Exception:
            return None, None, None

    def _extract_objections(self, turns: list) -> list[str]:
        """Extract objection signals from turn output payloads."""
        objections: list[str] = []
        for turn in turns:
            payload = turn.output_payload or {}
            detected = payload.get("objections_detected", [])
            if isinstance(detected, list):
                objections.extend(detected)
        return list(dict.fromkeys(objections))

    def _extract_key_moments(self, turns: list) -> list[str]:
        """Extract key moments from emotional signals and interruptions."""
        moments: list[str] = []
        for turn in turns:
            signal = getattr(turn, "emotional_signal", None)
            if signal and signal not in ("neutral", "unknown"):
                moments.append(f"Turn {turn.turn_index}: {signal}")
            if getattr(turn, "handoff_recommended", False):
                moments.append(f"Turn {turn.turn_index}: handoff flagged")
        return moments[-10:]

    def _derive_emotional_state(self, turns: list, signals) -> str:
        """Derive current emotional state from recent turns."""
        if not turns:
            return "unknown"
        recent = turns[-3:]
        signals_seen = [
            getattr(t, "emotional_signal", None)
            for t in recent
            if getattr(t, "emotional_signal", None)
        ]
        if not signals_seen:
            if signals.trust_score >= 7.0:
                return "receptive"
            if signals.trust_score >= 4.0:
                return "neutral"
            return "guarded"
        from collections import Counter
        most_common = Counter(signals_seen).most_common(1)[0][0]
        return most_common

    def _derive_motivation(self, turns: list) -> str | None:
        """Extract motivation from turn payloads."""
        for turn in reversed(turns):
            payload = turn.output_payload or {}
            motivation = payload.get("seller_motivation")
            if motivation:
                return motivation
        return None

    def _extract_timeline(self, turns: list) -> str | None:
        """Extract timeline from turn payloads."""
        for turn in reversed(turns):
            payload = turn.output_payload or {}
            timeline = payload.get("seller_timeline")
            if timeline:
                return timeline
        return None

    def _build_summary(
        self,
        seller_name: str | None,
        signals,
        transfer_reason: TransferReason,
        turn_count: int,
        objections: list[str],
        key_moments: list[str],
    ) -> str:
        name = seller_name or "the seller"
        heat = f"{signals.deal_heat:.1f}/10"
        trust = f"{signals.trust_score:.1f}/10"
        reason_label = transfer_reason.value.replace("_", " ")

        parts = [
            f"Transfer reason: {reason_label}.",
            f"{name} is {turn_count} turns into the conversation.",
            f"Deal heat: {heat}. Trust: {trust}.",
        ]
        if objections:
            parts.append(f"Objections raised: {', '.join(objections[:3])}.")
        if key_moments:
            parts.append(f"Key moments: {'; '.join(key_moments[-3:])}.")
        parts.append("Take over naturally — seller does not know they are being transferred.")

        return " ".join(parts)