"""
AI task contracts — immutable input/output/result types.

All dataclasses are frozen. No mutable state crosses runtime boundaries.
These are the only types that flow between the provider abstraction and callers.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from models.enums import AIExecutionStatus, AIProviderType, AITaskType

_DEFAULT_MODEL = "claude-sonnet-4-6"


@dataclass(frozen=True)
class AITaskInput:
    """Immutable descriptor of a single AI task to execute."""

    task_type: AITaskType
    payload: dict
    execution_key: str  # Caller-supplied idempotency key
    provider: AIProviderType = AIProviderType.anthropic
    model_name: str = _DEFAULT_MODEL


@dataclass(frozen=True)
class AIExecutionBounds:
    """Hard limits for a single execution attempt."""

    token_budget: int = 4096
    timeout_seconds: int = 30
    max_attempts: int = 3


@dataclass(frozen=True)
class AITaskOutput:
    """Raw output returned by a provider after successful execution."""

    output: dict
    tokens_used: int
    model_name: str


@dataclass(frozen=True)
class AIExecutionResult:
    """Full result returned to callers after execution completes/fails/cancels."""

    execution_id: UUID
    execution_key: str
    status: AIExecutionStatus
    output: dict | None
    tokens_used: int | None
    attempt: int
    error: str | None = None
    checkpoint_state: dict | None = None


@dataclass(frozen=True)
class AIToolCallRequest:
    """Request to invoke a registered tool during an AI execution."""

    execution_id: UUID
    tool_id: str
    tool_input: dict
    call_key: str  # idempotency key for this specific tool call
    requires_approval: bool = False


@dataclass(frozen=True)
class AIToolCallResult:
    """Result of a tool invocation."""

    execution_id: UUID
    tool_id: str
    call_key: str
    output: dict
    approved: bool = True
    error: str | None = None
