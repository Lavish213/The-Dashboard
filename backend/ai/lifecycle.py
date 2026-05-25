"""
AIExecutionRuntime — deterministic AI execution lifecycle manager.

State machine:
  pending → running → completed
                    → failed  (→ retry: pending if attempts remain)
                    → awaiting_approval → running
                    → cancelled (from any non-terminal state)

All mutations:
  - persist to ai_executions row (SELECT FOR UPDATE)
  - emit domain event via event_emitter

Idempotency:
  create()  — returns existing row if execution_key already exists
  cancel()  — no-op if already terminal
  complete() / fail() — raise if not in running state

Append-only semantics:
  started_at, completed_at, cancelled_at are set once and never cleared.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ai.context import AIExecutionContext
from ai.contracts import AIExecutionResult
from events.contracts import DomainEvent
from events.emitter import event_emitter
from models.ai_execution import AIExecution
from models.enums import AIExecutionStatus
from repositories.ai_execution import AIExecutionRepository

logger = structlog.get_logger(__name__)

AI_CHANNEL = "ai"

EVT_CREATED = "ai.execution.created"
EVT_STARTED = "ai.execution.started"
EVT_COMPLETED = "ai.execution.completed"
EVT_FAILED = "ai.execution.failed"
EVT_CANCELLED = "ai.execution.cancelled"
EVT_CHECKPOINTED = "ai.execution.checkpointed"
EVT_APPROVAL_REQUIRED = "ai.execution.approval_required"
EVT_RETRY_SCHEDULED = "ai.execution.retry_scheduled"
EVT_RESUMED = "ai.execution.resumed"

_TERMINAL = frozenset({
    AIExecutionStatus.completed,
    AIExecutionStatus.cancelled,
})


class AIExecutionStateError(Exception):
    """Raised on illegal state transitions."""


class AIExecutionRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AIExecutionRepository(session)

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------

    async def create(
        self,
        context: AIExecutionContext,
        requires_approval: bool = False,
    ) -> AIExecutionResult:
        """
        Create a new execution row. Idempotent: if execution_key already
        exists, returns the existing result without creating a duplicate.
        """
        existing = await self._repo.get_by_key(context.execution_key)
        if existing is not None:
            return _to_result(existing)

        row = AIExecution(
            execution_key=context.execution_key,
            task_type=context.task_input.task_type,
            provider=context.task_input.provider,
            model_name=context.task_input.model_name,
            status=AIExecutionStatus.pending,
            workflow_id=context.workflow_id,
            correlation_id=context.correlation_id,
            input_payload=context.task_input.payload,
            token_budget=context.bounds.token_budget,
            timeout_seconds=context.bounds.timeout_seconds,
            max_attempts=context.bounds.max_attempts,
            requires_approval=requires_approval,
            actor_id=context.actor_id,
            checkpoint_state=context.checkpoint_state,
        )
        self._session.add(row)
        await self._session.flush()

        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=AI_CHANNEL,
                event_type=EVT_CREATED,
                payload={
                    "execution_id": str(row.id),
                    "execution_key": row.execution_key,
                    "task_type": str(row.task_type),
                    "provider": str(row.provider),
                    "model_name": row.model_name,
                    "workflow_id": str(context.workflow_id) if context.workflow_id else None,
                },
                correlation_id=context.correlation_id,
            ),
        )

        logger.info("ai.execution.created", execution_id=str(row.id), key=row.execution_key)
        return _to_result(row)

    # ------------------------------------------------------------------
    # start
    # ------------------------------------------------------------------

    async def start(self, execution_id: UUID) -> AIExecutionResult:
        """
        pending → running. Sets started_at, increments attempt.
        Raises AIExecutionStateError if not in pending state.
        """
        row = await self._repo.get_for_update_or_raise(execution_id)
        if row.status != AIExecutionStatus.pending:
            raise AIExecutionStateError(
                f"cannot start execution in state {row.status}"
            )

        row.status = AIExecutionStatus.running
        row.started_at = datetime.now(UTC)
        row.attempt = (row.attempt or 0) + 1
        self._session.add(row)
        await self._session.flush()

        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=AI_CHANNEL,
                event_type=EVT_STARTED,
                payload={
                    "execution_id": str(execution_id),
                    "attempt": row.attempt,
                    "model_name": row.model_name,
                },
                correlation_id=row.correlation_id,
            ),
        )

        logger.info("ai.execution.started", execution_id=str(execution_id), attempt=row.attempt)
        return _to_result(row)

    # ------------------------------------------------------------------
    # complete
    # ------------------------------------------------------------------

    async def complete(
        self,
        execution_id: UUID,
        output: dict,
        tokens_used: int,
    ) -> AIExecutionResult:
        """
        running → completed. Records output and tokens_used.
        Raises AIExecutionStateError if not running.
        """
        row = await self._repo.get_for_update_or_raise(execution_id)
        if row.status != AIExecutionStatus.running:
            raise AIExecutionStateError(
                f"cannot complete execution in state {row.status}"
            )

        row.status = AIExecutionStatus.completed
        row.output_payload = output
        row.tokens_used = tokens_used
        row.completed_at = datetime.now(UTC)
        self._session.add(row)
        await self._session.flush()

        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=AI_CHANNEL,
                event_type=EVT_COMPLETED,
                payload={
                    "execution_id": str(execution_id),
                    "tokens_used": tokens_used,
                    "attempt": row.attempt,
                },
                correlation_id=row.correlation_id,
            ),
        )

        logger.info("ai.execution.completed", execution_id=str(execution_id), tokens=tokens_used)
        return _to_result(row)

    # ------------------------------------------------------------------
    # fail
    # ------------------------------------------------------------------

    async def fail(
        self,
        execution_id: UUID,
        error: str,
    ) -> AIExecutionResult:
        """
        running → failed.
        If attempt < max_attempts: resets to pending (retry eligible).
        Otherwise: stays failed (exhausted).
        """
        row = await self._repo.get_for_update_or_raise(execution_id)
        if row.status != AIExecutionStatus.running:
            raise AIExecutionStateError(
                f"cannot fail execution in state {row.status}"
            )

        row.error = error
        attempt = row.attempt or 0
        max_attempts = row.max_attempts or 1

        if attempt < max_attempts:
            # Retry eligible — reset to pending so start() can re-try
            row.status = AIExecutionStatus.pending
            row.started_at = None
            self._session.add(row)
            await self._session.flush()

            await event_emitter.emit(
                self._session,
                DomainEvent(
                    channel=AI_CHANNEL,
                    event_type=EVT_RETRY_SCHEDULED,
                    payload={
                        "execution_id": str(execution_id),
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                        "error": error,
                    },
                    correlation_id=row.correlation_id,
                ),
            )
            logger.info(
                "ai.execution.retry_scheduled",
                execution_id=str(execution_id),
                attempt=attempt,
            )
        else:
            row.status = AIExecutionStatus.failed
            self._session.add(row)
            await self._session.flush()

            await event_emitter.emit(
                self._session,
                DomainEvent(
                    channel=AI_CHANNEL,
                    event_type=EVT_FAILED,
                    payload={
                        "execution_id": str(execution_id),
                        "error": error,
                        "attempt": attempt,
                    },
                    correlation_id=row.correlation_id,
                ),
            )
            logger.info("ai.execution.failed", execution_id=str(execution_id), error=error)

        return _to_result(row)

    # ------------------------------------------------------------------
    # cancel
    # ------------------------------------------------------------------

    async def cancel(
        self,
        execution_id: UUID,
        reason: str = "",
    ) -> AIExecutionResult:
        """
        Cancel from any non-terminal state. Idempotent — no-op if already terminal.
        """
        row = await self._repo.get_for_update_or_raise(execution_id)

        if row.status in _TERMINAL:
            return _to_result(row)

        row.status = AIExecutionStatus.cancelled
        row.cancelled_at = datetime.now(UTC)
        row.cancel_reason = reason or None
        self._session.add(row)
        await self._session.flush()

        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=AI_CHANNEL,
                event_type=EVT_CANCELLED,
                payload={
                    "execution_id": str(execution_id),
                    "reason": reason,
                },
                correlation_id=row.correlation_id,
            ),
        )

        logger.info("ai.execution.cancelled", execution_id=str(execution_id), reason=reason)
        return _to_result(row)

    # ------------------------------------------------------------------
    # checkpoint
    # ------------------------------------------------------------------

    async def checkpoint(
        self,
        execution_id: UUID,
        state: dict,
    ) -> None:
        """
        Save resumable state blob to checkpoint_state.
        Only valid while running. Overwrites previous checkpoint.
        """
        row = await self._repo.get_for_update_or_raise(execution_id)
        if row.status != AIExecutionStatus.running:
            raise AIExecutionStateError(
                f"cannot checkpoint execution in state {row.status}"
            )

        row.checkpoint_state = state
        self._session.add(row)
        await self._session.flush()

        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=AI_CHANNEL,
                event_type=EVT_CHECKPOINTED,
                payload={
                    "execution_id": str(execution_id),
                    "checkpoint_keys": list(state.keys()),
                },
                correlation_id=row.correlation_id,
            ),
        )

        logger.info("ai.execution.checkpointed", execution_id=str(execution_id))

    # ------------------------------------------------------------------
    # approval gate transitions
    # ------------------------------------------------------------------

    async def mark_awaiting_approval(
        self,
        execution_id: UUID,
        approval_id: UUID,
    ) -> AIExecutionResult:
        """running → awaiting_approval. Links approval_id."""
        row = await self._repo.get_for_update_or_raise(execution_id)
        if row.status != AIExecutionStatus.running:
            raise AIExecutionStateError(
                f"cannot pause for approval in state {row.status}"
            )

        row.status = AIExecutionStatus.awaiting_approval
        row.approval_id = approval_id
        self._session.add(row)
        await self._session.flush()

        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=AI_CHANNEL,
                event_type=EVT_APPROVAL_REQUIRED,
                payload={
                    "execution_id": str(execution_id),
                    "approval_id": str(approval_id),
                },
                correlation_id=row.correlation_id,
            ),
        )

        logger.info(
            "ai.execution.approval_required",
            execution_id=str(execution_id),
            approval_id=str(approval_id),
        )
        return _to_result(row)

    async def resume_from_approval(self, execution_id: UUID) -> AIExecutionResult:
        """awaiting_approval → running (approval granted)."""
        row = await self._repo.get_for_update_or_raise(execution_id)
        if row.status != AIExecutionStatus.awaiting_approval:
            raise AIExecutionStateError(
                f"cannot resume from approval in state {row.status}"
            )

        row.status = AIExecutionStatus.running
        self._session.add(row)
        await self._session.flush()

        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=AI_CHANNEL,
                event_type=EVT_RESUMED,
                payload={"execution_id": str(execution_id)},
                correlation_id=row.correlation_id,
            ),
        )

        logger.info("ai.execution.resumed", execution_id=str(execution_id))
        return _to_result(row)


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

def _to_result(row: AIExecution) -> AIExecutionResult:
    return AIExecutionResult(
        execution_id=row.id,
        execution_key=row.execution_key,
        status=row.status,
        output=row.output_payload,
        tokens_used=row.tokens_used,
        attempt=row.attempt,
        error=row.error,
        checkpoint_state=row.checkpoint_state,
    )
