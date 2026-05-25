"""
ResearchReplayRuntime — deterministic replay foundation for research jobs.

Reconstructs the ordered event sequence from research_events.
Read-only — no side effects.
Foundation for replay debugging, audit review, and future deterministic
re-execution from a known checkpoint.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.research_event import ResearchEventRepository
from research.contracts import ResearchReplayFrame


class ResearchReplayRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = ResearchEventRepository(session)

    async def get_frames(self, job_id: UUID) -> list[ResearchReplayFrame]:
        """
        Return ordered replay frames for a job.
        Each frame corresponds to one ResearchEvent in emission order.
        """
        events = await self._events.get_for_job(job_id)
        return [
            ResearchReplayFrame(
                frame_index=idx,
                event_type=event.event_type.value,
                job_id=job_id,
                task_id=event.task_id,
                payload=event.payload,
                emitted_at=event.emitted_at,
            )
            for idx, event in enumerate(events)
        ]

    async def get_task_frames(self, task_id: UUID) -> list[ResearchReplayFrame]:
        """Return ordered replay frames for a single task."""
        events = await self._events.get_for_task(task_id)
        return [
            ResearchReplayFrame(
                frame_index=idx,
                event_type=event.event_type.value,
                job_id=event.job_id or UUID(int=0),
                task_id=task_id,
                payload=event.payload,
                emitted_at=event.emitted_at,
            )
            for idx, event in enumerate(events)
        ]

    async def reconstruct_status(self, job_id: UUID) -> dict:
        """
        Reconstruct job status progression from events.
        Returns a dict mapping frame_index → event_type for status-changing events.
        """
        frames = await self.get_frames(job_id)
        status_events = {
            "job_created",
            "job_started",
            "job_paused",
            "job_resumed",
            "job_completed",
            "job_failed",
            "job_cancelled",
        }
        return {
            f.frame_index: f.event_type
            for f in frames
            if f.event_type in status_events
        }
