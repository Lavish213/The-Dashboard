"""
ContextBudgetEnforcer — token budget enforcement at 5 levels.

Levels (from TOKEN_BUDGETS.md): platform → phase → graph → agent → call.
Each level has its own budget; enforcement is strictly additive downward.

Pure/stateless — no I/O. Raises ContextBudgetExceededError on violation.
Fail-closed: zero or negative budget always raises.
"""
from __future__ import annotations

from context.exceptions import ContextBudgetExceededError
from models.enums import ContextBudgetLevel

# Ordered hierarchy from broadest to narrowest
_LEVEL_ORDER: list[ContextBudgetLevel] = [
    ContextBudgetLevel.platform,
    ContextBudgetLevel.phase,
    ContextBudgetLevel.graph,
    ContextBudgetLevel.agent,
    ContextBudgetLevel.call,
]


class ContextBudgetEnforcer:
    """
    Stateless token budget enforcer.

    enforce(level, actual, budget, scope) — raises if actual > budget.
    enforce_all(usage, budgets, scope) — check all levels at once.
    """

    def enforce(
        self,
        level: ContextBudgetLevel,
        actual: int,
        budget: int,
        scope: str | None = None,
    ) -> None:
        """
        Raise ContextBudgetExceededError if actual > budget.
        A zero or negative budget always fails (fail-closed).
        """
        if budget <= 0 or actual > budget:
            raise ContextBudgetExceededError(
                level=level.value,
                budget=budget,
                actual=actual,
                scope=scope,
            )

    def enforce_all(
        self,
        usage: dict[ContextBudgetLevel, int],
        budgets: dict[ContextBudgetLevel, int],
        scope: str | None = None,
    ) -> None:
        """
        Check all levels in hierarchy order. Raises on first violation.
        Levels not present in either dict are skipped.
        """
        for level in _LEVEL_ORDER:
            if level not in usage or level not in budgets:
                continue
            self.enforce(level, usage[level], budgets[level], scope=scope)

    def within_budget(
        self,
        level: ContextBudgetLevel,
        actual: int,
        budget: int,
    ) -> bool:
        """Non-raising check. Returns True if actual <= budget > 0."""
        return budget > 0 and actual <= budget
