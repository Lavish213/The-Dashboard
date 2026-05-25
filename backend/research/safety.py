"""
ResearchSafetyRuntime — execution ceiling enforcement for research jobs.

Enforces:
- token budget with warning threshold
- recursion/depth guards
- task count ceiling
- dead-letter recording for orphaned tasks
- timeout detection primitives

No orchestration logic. Pure enforcement layer.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import ResearchEventType
from repositories.research_event import ResearchEventRepository
from repositories.research_job import ResearchJobRepository
from research.contracts import ResearchBudgetState, ResearchSafetyConfig


class ResearchBudgetExceededError(Exception):
    pass


class ResearchDepthExceededError(Exception):
    pass


class ResearchTaskLimitExceededError(Exception):
    pass


class ResearchSafetyRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jobs = ResearchJobRepository(session)
        self._events = ResearchEventRepository(session)

    async def check_budget(
        self,
        job_id: UUID,
        config: ResearchSafetyConfig,
        tokens_to_add: int = 0,
    ) -> ResearchBudgetState:
        """
        Check token budget for a job.
        Emits budget_warning if near threshold.
        Raises ResearchBudgetExceededError if over budget.
        Does not modify job state.
        """
        row = await self._jobs.get(job_id)
        if row is None:
            raise ValueError(f"Job {job_id} not found")

        projected_used = row.tokens_used + tokens_to_add
        fraction = projected_used / config.max_tokens if config.max_tokens > 0 else 1.0
        near_limit = fraction >= config.token_warning_threshold
        over_budget = projected_used > config.max_tokens

        state = ResearchBudgetState(
            job_id=job_id,
            tokens_used=projected_used,
            token_budget=config.max_tokens,
            tokens_remaining=max(0, config.max_tokens - projected_used),
            budget_fraction=fraction,
            over_budget=over_budget,
            near_limit=near_limit,
            task_count=row.task_count,
            current_depth=row.current_depth,
        )

        if near_limit and not over_budget:
            await self._events.append(
                ResearchEventType.budget_warning,
                job_id=job_id,
                payload={
                    "tokens_used": projected_used,
                    "token_budget": config.max_tokens,
                    "fraction": round(fraction, 3),
                },
            )

        if over_budget:
            await self._events.append(
                ResearchEventType.budget_exceeded,
                job_id=job_id,
                payload={
                    "tokens_used": projected_used,
                    "token_budget": config.max_tokens,
                },
            )
            raise ResearchBudgetExceededError(
                f"Job {job_id} token budget exceeded: "
                f"{projected_used} > {config.max_tokens}"
            )

        return state

    async def check_depth(
        self,
        job_id: UUID,
        proposed_depth: int,
        config: ResearchSafetyConfig,
    ) -> None:
        """
        Raise ResearchDepthExceededError if proposed_depth > config.max_depth.
        Emits depth_limit_reached event.
        """
        if proposed_depth > config.max_depth:
            await self._events.append(
                ResearchEventType.depth_limit_reached,
                job_id=job_id,
                payload={
                    "proposed_depth": proposed_depth,
                    "max_depth": config.max_depth,
                },
            )
            raise ResearchDepthExceededError(
                f"Job {job_id} depth {proposed_depth} exceeds limit {config.max_depth}"
            )

    async def check_task_limit(
        self,
        job_id: UUID,
        config: ResearchSafetyConfig,
    ) -> None:
        """
        Raise ResearchTaskLimitExceededError if task_count >= max_tasks.
        """
        row = await self._jobs.get(job_id)
        if row is None:
            raise ValueError(f"Job {job_id} not found")

        if row.task_count >= config.max_tasks:
            raise ResearchTaskLimitExceededError(
                f"Job {job_id} task count {row.task_count} >= limit {config.max_tasks}"
            )

    async def check_timeout(
        self,
        job_id: UUID,
        config: ResearchSafetyConfig,
    ) -> bool:
        """
        Returns True if job has exceeded its timeout (based on started_at).
        Emits timeout_triggered event and returns True.
        Does NOT cancel the job — caller is responsible for that.
        """
        if config.timeout_seconds is None:
            return False

        row = await self._jobs.get(job_id)
        if row is None or row.started_at is None:
            return False

        elapsed = (datetime.now(UTC) - row.started_at).total_seconds()
        if elapsed > config.timeout_seconds:
            await self._events.append(
                ResearchEventType.timeout_triggered,
                job_id=job_id,
                payload={
                    "elapsed_seconds": elapsed,
                    "timeout_seconds": config.timeout_seconds,
                },
            )
            return True

        return False

    async def record_dead_letter(
        self,
        job_id: UUID,
        task_id: UUID | None,
        reason: str,
        context: dict | None = None,
    ) -> None:
        """
        Record an unhandleable item to the dead-letter event log.
        Does not modify any row — append-only signal for operator review.
        """
        await self._events.append(
            ResearchEventType.dead_letter,
            job_id=job_id,
            task_id=task_id,
            payload={
                "reason": reason,
                "context": context or {},
                "recorded_at": datetime.now(UTC).isoformat(),
            },
        )
