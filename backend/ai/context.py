"""
AIExecutionContext — runtime scope bundle for a single AI execution.

Passed to providers and runtime primitives. Immutable — callers may not
modify context after construction. checkpoint_state carries resume payload
when restarting a previously checkpointed execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ai.contracts import AIExecutionBounds, AITaskInput


@dataclass(frozen=True)
class AIExecutionContext:
    """All runtime state scoped to one AI execution attempt."""

    execution_id: UUID
    execution_key: str
    task_input: AITaskInput
    bounds: AIExecutionBounds
    workflow_id: UUID | None = None
    correlation_id: str | None = None
    actor_id: UUID | None = None
    # Non-None when resuming a previously checkpointed execution.
    checkpoint_state: dict | None = None
