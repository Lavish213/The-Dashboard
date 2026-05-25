"""
ContextWindowRuntime — bounded windowing with deterministic truncation.

Applies a TruncationPolicy to a list of ContextItems to produce a
ContextWindow that fits within the token budget. All operations are
pure / side-effect free — no DB writes.

Truncation strategies:
  truncate_oldest           — remove items with the largest created_at first
  truncate_lowest_priority  — remove items with the highest priority number first
  truncate_largest          — remove largest items (by token_count) first
  fail_on_overflow          — raise ContextWindowOverflowError if over budget

Protected layers (system by default) are never removed.
"""
from __future__ import annotations

from context.contracts import ContextItem, ContextWindow, TruncationPolicy
from models.enums import ContextWindowStrategy


class ContextWindowOverflowError(Exception):
    """Raised when fail_on_overflow strategy is used and budget is exceeded."""

    def __init__(self, total_tokens: int, budget: int) -> None:
        self.total_tokens = total_tokens
        self.budget = budget
        super().__init__(
            f"Context window overflow: {total_tokens} tokens exceeds budget {budget}"
        )


class ContextWindowRuntime:
    """
    Pure context window assembler. No I/O.

    build(items, budget, policy) → ContextWindow
    """

    def build(
        self,
        items: list[ContextItem],
        budget: int,
        policy: TruncationPolicy,
    ) -> ContextWindow:
        """
        Assemble a bounded context window from items.

        Items are sorted by (priority ASC, created_at ASC) — lower priority
        number = higher importance = kept last when truncating.

        Returns a ContextWindow with items ordered by (priority ASC) ready
        for injection (highest priority items appear last = most recent
        in model context).
        """
        if policy.max_items is not None:
            items = items[: policy.max_items]

        # Sort: priority ASC (0 = most important), then created_at ASC (oldest first)
        def sort_key(item: ContextItem) -> tuple:
            ts = item.created_at.timestamp() if item.created_at else 0.0
            return (item.priority, ts)

        sorted_items = sorted(items, key=sort_key)
        total = sum(i.token_count for i in sorted_items)

        if total <= budget:
            return ContextWindow(
                items=tuple(sorted_items),
                total_tokens=total,
                token_budget=budget,
                truncated=False,
                truncated_count=0,
                strategy=policy.strategy,
            )

        if policy.strategy == ContextWindowStrategy.fail_on_overflow:
            raise ContextWindowOverflowError(total, budget)

        kept, dropped = self._truncate(sorted_items, budget, policy)
        return ContextWindow(
            items=tuple(kept),
            total_tokens=sum(i.token_count for i in kept),
            token_budget=budget,
            truncated=True,
            truncated_count=dropped,
            strategy=policy.strategy,
        )

    def _truncate(
        self,
        items: list[ContextItem],
        budget: int,
        policy: TruncationPolicy,
    ) -> tuple[list[ContextItem], int]:
        """Remove items until total_tokens <= budget. Protected layers are never removed."""
        protected = set(policy.protect_layers)
        mutable = [i for i in items if i.layer not in protected]
        fixed = [i for i in items if i.layer in protected]

        strategy = policy.strategy

        if strategy == ContextWindowStrategy.truncate_oldest:
            # Remove oldest (smallest created_at) first — already sorted oldest-first
            candidates = list(mutable)
        elif strategy == ContextWindowStrategy.truncate_lowest_priority:
            # Remove highest priority number (least important) first
            candidates = sorted(mutable, key=lambda i: -i.priority)
        elif strategy == ContextWindowStrategy.truncate_largest:
            # Remove largest items first
            candidates = sorted(mutable, key=lambda i: -i.token_count)
        else:
            candidates = list(mutable)

        kept_mutable = list(candidates)
        dropped = 0
        current_total = sum(i.token_count for i in fixed) + sum(
            i.token_count for i in kept_mutable
        )

        while current_total > budget and kept_mutable:
            removed = kept_mutable.pop(0)
            current_total -= removed.token_count
            dropped += 1

        # Re-sort kept items by original priority/time order
        def sort_key(item: ContextItem) -> tuple:
            ts = item.created_at.timestamp() if item.created_at else 0.0
            return (item.priority, ts)

        final = sorted(fixed + kept_mutable, key=sort_key)
        return final, dropped
