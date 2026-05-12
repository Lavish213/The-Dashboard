"""
CallBroadcaster — publishes typed call events to `call:{session_id}` channels.
Sequence tracking for reconnect safety. Incremental only — never full state dumps.
"""
from __future__ import annotations

from uuid import UUID

from realtime.broadcast import broadcast_service
from realtime.protocol import RealtimeEvent

EVT_SESSION_CREATED = "call.session_created"
EVT_SESSION_STARTED = "call.session_started"
EVT_SESSION_COMPLETED = "call.session_completed"
EVT_SESSION_FAILED = "call.session_failed"
EVT_PARTICIPANT_JOINED = "call.participant_joined"
EVT_PARTICIPANT_LEFT = "call.participant_left"
EVT_PARTICIPANT_RECONNECTED = "call.participant_reconnected"
EVT_PARTICIPANT_DROPPED = "call.participant_dropped"
EVT_HEARTBEAT = "call.heartbeat"


def _call_channel(session_id: UUID) -> str:
    return f"call:{session_id}"


class CallBroadcaster:
    async def publish(
        self,
        session_id: UUID,
        event_type: str,
        payload: dict,
        sequence: int,
    ) -> int:
        channel = _call_channel(session_id)
        event = RealtimeEvent(
            channel=channel,
            event_type=event_type,
            payload={
                "session_id": str(session_id),
                "sequence": sequence,
                **payload,
            },
        )
        return await broadcast_service.publish(event)

    async def publish_session_created(self, session_id: UUID, sequence: int) -> int:
        return await self.publish(session_id, EVT_SESSION_CREATED, {}, sequence)

    async def publish_session_started(self, session_id: UUID, sequence: int) -> int:
        return await self.publish(session_id, EVT_SESSION_STARTED, {}, sequence)

    async def publish_session_completed(self, session_id: UUID, sequence: int) -> int:
        return await self.publish(session_id, EVT_SESSION_COMPLETED, {}, sequence)

    async def publish_session_failed(self, session_id: UUID, reason: str, sequence: int) -> int:
        return await self.publish(
            session_id, EVT_SESSION_FAILED, {"reason": reason}, sequence
        )

    async def publish_participant_joined(
        self,
        session_id: UUID,
        participant_id: UUID,
        role: str,
        sequence: int,
    ) -> int:
        return await self.publish(
            session_id,
            EVT_PARTICIPANT_JOINED,
            {"participant_id": str(participant_id), "role": role},
            sequence,
        )

    async def publish_participant_left(
        self,
        session_id: UUID,
        participant_id: UUID,
        sequence: int,
    ) -> int:
        return await self.publish(
            session_id,
            EVT_PARTICIPANT_LEFT,
            {"participant_id": str(participant_id)},
            sequence,
        )

    async def publish_participant_reconnected(
        self,
        session_id: UUID,
        participant_id: UUID,
        sequence: int,
    ) -> int:
        return await self.publish(
            session_id,
            EVT_PARTICIPANT_RECONNECTED,
            {"participant_id": str(participant_id)},
            sequence,
        )

    async def publish_participant_dropped(
        self,
        session_id: UUID,
        participant_id: UUID,
        sequence: int,
    ) -> int:
        return await self.publish(
            session_id,
            EVT_PARTICIPANT_DROPPED,
            {"participant_id": str(participant_id)},
            sequence,
        )


# Module-level singleton
call_broadcaster = CallBroadcaster()
