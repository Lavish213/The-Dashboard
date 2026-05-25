"""
Context error hierarchy — Phase 15.

ContextError
  ContextBudgetExceededError — token budget exceeded at a specific level
  ContextSanitizationError   — unsafe content detected during sanitization
  ContextReplayError         — replay reconstruction failed or blocked
  ContextMemoryError         — memory scope violation or budget overflow

Note: ContextGuardrailError lives in context/guardrails.py — not duplicated here.
"""
from __future__ import annotations

from uuid import UUID


class ContextError(Exception):
    """Base class for all context runtime errors."""


class ContextBudgetExceededError(ContextError):
    """Raised when token usage exceeds the budget at a specific level."""

    def __init__(
        self,
        level: str,
        budget: int,
        actual: int,
        scope: str | None = None,
    ) -> None:
        self.level = level
        self.budget = budget
        self.actual = actual
        self.scope = scope
        detail = f"scope={scope} " if scope else ""
        super().__init__(
            f"Token budget exceeded at level={level}: {detail}{actual} > {budget}"
        )


class ContextSanitizationError(ContextError):
    """Raised when unsafe or secret content is detected in a context item."""

    def __init__(self, reason: str, field: str | None = None) -> None:
        self.reason = reason
        self.field = field
        detail = f" (field={field})" if field else ""
        super().__init__(f"Sanitization failed{detail}: {reason}")


class ContextReplayError(ContextError):
    """Raised when replay reconstruction is blocked or fails."""

    def __init__(self, snapshot_id: UUID | str, reason: str) -> None:
        self.snapshot_id = snapshot_id
        self.reason = reason
        super().__init__(f"Replay failed for snapshot {snapshot_id}: {reason}")


class ContextMemoryError(ContextError):
    """Raised on memory scope violation or budget overflow."""

    def __init__(self, scope: str, reason: str) -> None:
        self.scope = scope
        self.reason = reason
        super().__init__(f"Memory error for scope={scope}: {reason}")
