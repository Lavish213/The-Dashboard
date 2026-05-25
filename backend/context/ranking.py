"""
ContextItemRanker — deterministic ranking for context assembly.

Pure/stateless, no I/O. All rankings are deterministic: same input → same order.

Ranking strategies:
  by_priority — lowest priority number first (0 = highest), then oldest first
  by_recency  — newest first, then lowest priority first
  by_score    — caller-supplied scores dict, descending; ties broken by priority then age

Used before ContextWindowRuntime to select which items enter the budget window.
"""
from __future__ import annotations

from uuid import UUID

from context.contracts import ContextItem


class ContextItemRanker:
    """
    Stateless item ranker.

    rank_by_priority(items) → sorted list, most important first.
    rank_by_recency(items)  → sorted list, newest first.
    rank_by_score(items, scores) → sorted list, highest scored first.
    """

    def rank_by_priority(self, items: list[ContextItem]) -> list[ContextItem]:
        """
        Sort by priority ASC (lower number = higher priority),
        then by created_at ASC (older first) to break ties deterministically.
        """
        return sorted(items, key=lambda i: (i.priority, i.created_at))

    def rank_by_recency(self, items: list[ContextItem]) -> list[ContextItem]:
        """
        Sort by created_at DESC (newest first),
        then by priority ASC to break ties deterministically.
        """
        return sorted(items, key=lambda i: (-i.created_at.timestamp(), i.priority))

    def rank_by_score(
        self,
        items: list[ContextItem],
        scores: dict[UUID, float],
    ) -> list[ContextItem]:
        """
        Sort by caller-supplied score DESC, with ties broken by
        priority ASC then created_at ASC. Items missing from scores get 0.0.
        """
        return sorted(
            items,
            key=lambda i: (-scores.get(i.source_id, 0.0), i.priority, i.created_at),
        )

    def top_n(
        self,
        items: list[ContextItem],
        n: int,
        strategy: str = "priority",
        scores: dict[UUID, float] | None = None,
    ) -> list[ContextItem]:
        """
        Return top-n items by strategy.
        strategy: "priority" | "recency" | "score"
        """
        if strategy == "recency":
            ranked = self.rank_by_recency(items)
        elif strategy == "score":
            ranked = self.rank_by_score(items, scores or {})
        else:
            ranked = self.rank_by_priority(items)
        return ranked[:n]
