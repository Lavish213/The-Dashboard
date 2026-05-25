"""
Token budgeting primitives — enforce hard token limits per execution.

TokenBudget is a pure in-memory helper. It does NOT persist state.
Callers are responsible for recording tokens_used on the AIExecution row.

BudgetExhaustedError — raised when consume() would exceed the limit.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class BudgetExhaustedError(Exception):
    """Raised when an AI execution would exceed its token budget."""

    def __init__(self, requested: int, remaining: int, limit: int) -> None:
        super().__init__(
            f"token budget exhausted: requested {requested}, "
            f"remaining {remaining}/{limit}"
        )
        self.requested = requested
        self.remaining = remaining
        self.limit = limit


@dataclass
class TokenBudget:
    """
    Mutable in-memory token budget tracker.

    limit   — maximum tokens allowed for this execution
    used    — tokens consumed so far (cumulative across all calls)
    """

    limit: int
    used: int = field(default=0)

    def consume(self, tokens: int) -> None:
        """
        Record consumption of `tokens`.
        Raises BudgetExhaustedError if limit would be exceeded.
        """
        if tokens < 0:
            raise ValueError(f"tokens must be non-negative, got {tokens}")
        if self.used + tokens > self.limit:
            raise BudgetExhaustedError(
                requested=tokens,
                remaining=self.remaining,
                limit=self.limit,
            )
        self.used += tokens

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    @property
    def is_exhausted(self) -> bool:
        return self.used >= self.limit

    @property
    def utilization(self) -> float:
        """Fraction of budget used (0.0–1.0)."""
        if self.limit == 0:
            return 1.0
        return min(1.0, self.used / self.limit)
