"""
ContextCacheRuntime — in-process LRU cache keyed by assembly_key.

Cache entries are immutable ContextAssemblyResult values.
TTL is enforced at read time — expired entries are treated as misses.

This is an in-process cache only — no Redis, no cross-process sharing.
It is process-scoped and not durable across restarts.

set(assembly_key, result, ttl_seconds)
get(assembly_key) → ContextAssemblyResult | None
invalidate(assembly_key)
clear()
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from context.contracts import ContextAssemblyResult

_DEFAULT_TTL = 300  # 5 minutes
_DEFAULT_MAX_SIZE = 256


@dataclass
class _CacheEntry:
    result: ContextAssemblyResult
    expires_at: datetime


class ContextCacheRuntime:
    """
    In-process LRU-like cache for assembled context results.

    Eviction: LRU on overflow (pop oldest inserted key).
    TTL: per-entry expiry checked on read.
    """

    def __init__(self, max_size: int = _DEFAULT_MAX_SIZE) -> None:
        self._max_size = max_size
        # Insertion-order dict — oldest key first for LRU eviction
        self._store: dict[str, _CacheEntry] = {}

    def set(
        self,
        assembly_key: str,
        result: ContextAssemblyResult,
        ttl_seconds: int = _DEFAULT_TTL,
    ) -> None:
        """Store result under assembly_key with a TTL."""
        if assembly_key in self._store:
            del self._store[assembly_key]

        if len(self._store) >= self._max_size:
            # Evict oldest
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]

        expires_at = datetime.now(UTC).replace(
            microsecond=0
        )
        from datetime import timedelta
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)

        self._store[assembly_key] = _CacheEntry(result=result, expires_at=expires_at)

    def get(self, assembly_key: str) -> ContextAssemblyResult | None:
        """Return cached result or None if missing/expired."""
        entry = self._store.get(assembly_key)
        if entry is None:
            return None
        if datetime.now(UTC) > entry.expires_at:
            del self._store[assembly_key]
            return None
        return entry.result

    def invalidate(self, assembly_key: str) -> None:
        """Remove a single entry."""
        self._store.pop(assembly_key, None)

    def clear(self) -> None:
        """Remove all entries."""
        self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)
