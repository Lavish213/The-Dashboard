"""
Context infrastructure contracts — immutable input/output types.

All dataclasses are frozen. No mutable state crosses assembly boundaries.
These types flow between adapters, assembler, window, and snapshot runtimes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from models.enums import ContextLayerType, ContextWindowStrategy


@dataclass(frozen=True)
class ContextItem:
    """
    One unit of context from a single source.

    layer: which infrastructure layer this item belongs to.
    source_id: UUID of the originating entity (transcript_id, workflow_id, etc.).
    source_type: string discriminator matching the source table name.
    content: the text content to include in the context window.
    token_count: pre-computed token count for this item.
    priority: 0 = highest priority (kept last when truncating).
    metadata: arbitrary extra attribution data (immutable via tuple/frozenset).
    """

    layer: ContextLayerType
    source_id: UUID
    source_type: str
    content: str
    token_count: int
    priority: int = 0
    created_at: datetime | None = None
    metadata: dict = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash((self.layer, self.source_id, self.source_type, self.priority))


@dataclass(frozen=True)
class ContextWindow:
    """
    Assembled, bounded context window ready for injection.

    items: ordered list of ContextItem — deterministic order, highest priority last.
    total_tokens: sum of all item token counts.
    token_budget: budget limit this window was assembled against.
    truncated: True if items were dropped to fit within budget.
    truncated_count: number of items removed.
    strategy: windowing strategy used to truncate.
    """

    items: tuple[ContextItem, ...]
    total_tokens: int
    token_budget: int
    truncated: bool = False
    truncated_count: int = 0
    strategy: ContextWindowStrategy = ContextWindowStrategy.truncate_oldest


@dataclass(frozen=True)
class ContextAssemblyInput:
    """
    Input to the context assembler — specifies what to include and how.

    assembly_key: caller-supplied idempotency key.
    token_budget: hard upper bound on total tokens.
    layer_filter: if set, only include these layer types.
    workflow_id: optional scope restriction.
    transcript_id: optional scope restriction.
    execution_id: optional scope restriction.
    strategy: how to truncate when budget is exceeded.
    """

    assembly_key: str
    token_budget: int
    layer_filter: tuple[ContextLayerType, ...] | None = None
    workflow_id: UUID | None = None
    transcript_id: UUID | None = None
    execution_id: UUID | None = None
    strategy: ContextWindowStrategy = ContextWindowStrategy.truncate_oldest
    actor_id: UUID | None = None


@dataclass(frozen=True)
class ContextAssemblyResult:
    """
    Full result of a context assembly operation.

    snapshot_id: UUID of the persisted ContextSnapshot.
    assembly_key: mirrors the input assembly_key.
    window: the bounded context window.
    provenance: source attribution per layer.
    from_cache: True if result was served from cache, not assembled fresh.
    """

    snapshot_id: UUID
    assembly_key: str
    window: ContextWindow
    provenance: dict
    from_cache: bool = False


@dataclass(frozen=True)
class ContextProvenance:
    """
    Attribution record for one source in the assembled context.

    source_id: UUID of the contributing entity.
    source_type: discriminator string.
    layer: ContextLayerType.
    item_count: how many ContextItems came from this source.
    token_count: total tokens from this source.
    """

    source_id: UUID
    source_type: str
    layer: ContextLayerType
    item_count: int
    token_count: int


@dataclass(frozen=True)
class TruncationPolicy:
    """
    Policy governing how the window truncates when budget is exceeded.

    strategy: which algorithm to apply.
    protect_layers: layers that must never be truncated.
    max_items: optional hard cap on item count (applied before token limit).
    """

    strategy: ContextWindowStrategy = ContextWindowStrategy.truncate_oldest
    protect_layers: tuple[ContextLayerType, ...] = (ContextLayerType.system,)
    max_items: int | None = None


@dataclass(frozen=True)
class ContextRetentionPolicy:
    """Retention policy for context snapshots."""

    archive_after_days: int | None = None
    expire_after_days: int | None = None
    requires_explicit_delete: bool = True
