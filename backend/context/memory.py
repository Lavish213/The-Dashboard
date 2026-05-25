"""
ContextMemoryRuntime — bounded, scoped in-process context memory.

Hard rules (from Phase 15):
  - No unbounded memory injection
  - No hidden global memory — all memory is scope-keyed
  - No raw full transcript injection
  - Fail closed: budget overflow raises ContextMemoryError

Memory is in-process only — not persisted, not shared across processes.
Each scope has an independent token budget. Global scope is forbidden.

register(scope_id, item, budget) → add item to scope (raises if over budget)
load(scope_id) → list[ContextItem] for scope (empty list if scope unknown)
clear(scope_id) → remove all items for scope
total_tokens(scope_id) → current token count for scope
"""
from __future__ import annotations

from context.contracts import ContextItem
from context.exceptions import ContextMemoryError

_FORBIDDEN_SCOPE = "global"
_DEFAULT_SCOPE_BUDGET = 4096  # tokens per scope


class ContextMemoryRuntime:
    """
    Bounded, scoped in-process context memory store.

    Scope IDs must not be "global" — global state is forbidden.
    """

    def __init__(self) -> None:
        # scope_id → list of ContextItem
        self._store: dict[str, list[ContextItem]] = {}
        # scope_id → token budget
        self._budgets: dict[str, int] = {}

    def _validate_scope(self, scope_id: str) -> None:
        if scope_id == _FORBIDDEN_SCOPE:
            raise ContextMemoryError(
                scope=scope_id,
                reason="global scope is forbidden — all memory must be scoped",
            )
        if not scope_id or not scope_id.strip():
            raise ContextMemoryError(
                scope=scope_id,
                reason="scope_id must be a non-empty string",
            )

    def register(
        self,
        scope_id: str,
        item: ContextItem,
        budget: int = _DEFAULT_SCOPE_BUDGET,
    ) -> None:
        """
        Add item to scope. Raises ContextMemoryError if adding would exceed budget.
        Budget is set on first call for scope; ignored on subsequent calls.
        """
        self._validate_scope(scope_id)
        if scope_id not in self._store:
            self._store[scope_id] = []
            self._budgets[scope_id] = budget

        current_tokens = sum(i.token_count for i in self._store[scope_id])
        if current_tokens + item.token_count > self._budgets[scope_id]:
            raise ContextMemoryError(
                scope=scope_id,
                reason=(
                    f"budget exceeded: {current_tokens + item.token_count} > "
                    f"{self._budgets[scope_id]}"
                ),
            )

        self._store[scope_id].append(item)

    def load(self, scope_id: str) -> list[ContextItem]:
        """Return all items for scope, oldest first. Empty list if scope unknown."""
        self._validate_scope(scope_id)
        return list(self._store.get(scope_id, []))

    def clear(self, scope_id: str) -> None:
        """Remove all items for scope. No-op if scope unknown."""
        self._validate_scope(scope_id)
        self._store.pop(scope_id, None)
        self._budgets.pop(scope_id, None)

    def total_tokens(self, scope_id: str) -> int:
        """Return total token count for scope. Returns 0 if scope unknown."""
        self._validate_scope(scope_id)
        return sum(i.token_count for i in self._store.get(scope_id, []))

    def scope_exists(self, scope_id: str) -> bool:
        """Return True if scope has been registered."""
        return scope_id in self._store

    @property
    def active_scopes(self) -> list[str]:
        """Return list of all active scope IDs."""
        return list(self._store.keys())
