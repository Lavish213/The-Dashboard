"""
Transcript WebSocket broadcaster.

Publishes typed transcript events to `transcript:{transcript_id}` channels.
Sequence tracking for reconnect safety.
Never re-sends entire transcript — incremental only.
"""
from __future__ import annotations

from uuid import UUID

from realtime.broadcast import broadcast_service
from realtime.protocol import RealtimeEvent
from transcripts.runtime.runtime import (
    EVT_TRANSCRIPT_ARCHIVED,
    EVT_TRANSCRIPT_CHUNK_ADDED,
    EVT_TRANSCRIPT_COMPLETED,
    EVT_TRANSCRIPT_CREATED,
    EVT_TRANSCRIPT_FAILED,
    EVT_TRANSCRIPT_PAUSED,
    EVT_TRANSCRIPT_RESUMED,
    EVT_TRANSCRIPT_STARTED,
)


def _transcript_channel(transcript_id: UUID) -> str:
    return f"transcript:{transcript_id}"


class TranscriptBroadcaster:
    """
    Wraps BroadcastService with transcript-specific channel naming and typed payloads.
    publish() is fire-and-forget — callers do not need to await delivery.
    """

    async def publish(
        self,
        transcript_id: UUID,
        event_type: str,
        payload: dict,
        sequence: int,
    ) -> int:
        """Broadcast a transcript event. Returns subscriber count."""
        channel = _transcript_channel(transcript_id)
        event = RealtimeEvent(
            channel=channel,
            event_type=event_type,
            payload={
                "transcript_id": str(transcript_id),
                "sequence": sequence,
                **payload,
            },
        )
        return await broadcast_service.publish(event)

    async def publish_created(self, transcript_id: UUID, sequence: int, payload: dict) -> int:
        return await self.publish(transcript_id, EVT_TRANSCRIPT_CREATED, payload, sequence)

    async def publish_started(self, transcript_id: UUID, sequence: int) -> int:
        return await self.publish(transcript_id, EVT_TRANSCRIPT_STARTED, {}, sequence)

    async def publish_chunk(
        self,
        transcript_id: UUID,
        sequence: int,
        chunk_index: int,
        speaker: str,
        text: str,
        stream_type: str,
    ) -> int:
        return await self.publish(
            transcript_id,
            EVT_TRANSCRIPT_CHUNK_ADDED,
            {
                "chunk_index": chunk_index,
                "speaker": speaker,
                "text": text,
                "stream_type": stream_type,
            },
            sequence,
        )

    async def publish_paused(self, transcript_id: UUID, sequence: int, reason: str = "") -> int:
        return await self.publish(transcript_id, EVT_TRANSCRIPT_PAUSED, {"reason": reason}, sequence)

    async def publish_resumed(self, transcript_id: UUID, sequence: int) -> int:
        return await self.publish(transcript_id, EVT_TRANSCRIPT_RESUMED, {}, sequence)

    async def publish_completed(self, transcript_id: UUID, sequence: int) -> int:
        return await self.publish(transcript_id, EVT_TRANSCRIPT_COMPLETED, {}, sequence)

    async def publish_failed(self, transcript_id: UUID, sequence: int, reason: str = "") -> int:
        return await self.publish(transcript_id, EVT_TRANSCRIPT_FAILED, {"reason": reason}, sequence)

    async def publish_archived(self, transcript_id: UUID, sequence: int) -> int:
        return await self.publish(transcript_id, EVT_TRANSCRIPT_ARCHIVED, {}, sequence)


# Module-level singleton
transcript_broadcaster = TranscriptBroadcaster()
