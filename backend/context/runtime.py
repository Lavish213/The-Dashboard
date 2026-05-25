"""
ContextRuntime — session-scoped coordinator for all context primitives.

Lazy-initializes all context subsystems. Provides a unified entry point
for context assembly, replay, budget enforcement, and memory access.

All primitives follow the same lazy-init pattern as GovernanceRuntime
to avoid constructing unused objects.

assemble(input) → ContextAssemblyResult
reconstruct(snapshot_id) → ContextAssemblyResult
reconstruct_by_key(assembly_key) → ContextAssemblyResult
check_budget(level, actual, budget, scope) → None (raises on violation)
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from context.assembler import ContextAssembler
from context.audit import ContextAuditRuntime
from context.budget import ContextBudgetEnforcer
from context.cache import ContextCacheRuntime
from context.contracts import (
    ContextAssemblyInput,
    ContextAssemblyResult,
    ContextItem,
    TruncationPolicy,
)
from context.guardrails import ContextInjectionGuardrail
from context.ranking import ContextItemRanker
from context.replay import ContextReplayRuntime
from context.retention import ContextRetentionRuntime
from context.sanitizer import ContextItemSanitizer
from context.snapshot import ContextSnapshotRuntime
from models.enums import ContextBudgetLevel

# Shared in-process cache — one instance per process, not per session
_shared_cache = ContextCacheRuntime()


class ContextRuntime:
    """
    Session-scoped coordinator for all context primitives.

    Primitives are lazy-initialized on first access to avoid unnecessary
    object construction. Cache and memory are shared across sessions
    (in-process only).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

        # Lazy primitive handles
        self._assembler: ContextAssembler | None = None
        self._audit: ContextAuditRuntime | None = None
        self._guardrails: ContextInjectionGuardrail | None = None
        self._replay: ContextReplayRuntime | None = None
        self._retention: ContextRetentionRuntime | None = None
        self._snapshot: ContextSnapshotRuntime | None = None

        # Stateless / shared primitives (always constructed cheaply)
        self._budget = ContextBudgetEnforcer()
        self._ranker = ContextItemRanker()
        self._sanitizer = ContextItemSanitizer()

    # ------------------------------------------------------------------
    # Lazy properties — session-bound
    # ------------------------------------------------------------------

    @property
    def assembler(self) -> ContextAssembler:
        if self._assembler is None:
            self._assembler = ContextAssembler(self._session, cache=_shared_cache)
        return self._assembler

    @property
    def audit(self) -> ContextAuditRuntime:
        if self._audit is None:
            self._audit = ContextAuditRuntime(self._session)
        return self._audit

    @property
    def guardrails(self) -> ContextInjectionGuardrail:
        if self._guardrails is None:
            self._guardrails = ContextInjectionGuardrail()
        return self._guardrails

    @property
    def replay(self) -> ContextReplayRuntime:
        if self._replay is None:
            self._replay = ContextReplayRuntime(self._session)
        return self._replay

    @property
    def retention(self) -> ContextRetentionRuntime:
        if self._retention is None:
            self._retention = ContextRetentionRuntime(self._session)
        return self._retention

    @property
    def snapshot(self) -> ContextSnapshotRuntime:
        if self._snapshot is None:
            self._snapshot = ContextSnapshotRuntime(self._session)
        return self._snapshot

    # Stateless primitives — always available
    @property
    def budget(self) -> ContextBudgetEnforcer:
        return self._budget

    @property
    def ranker(self) -> ContextItemRanker:
        return self._ranker

    @property
    def sanitizer(self) -> ContextItemSanitizer:
        return self._sanitizer

    # ------------------------------------------------------------------
    # Coordinated operations
    # ------------------------------------------------------------------

    async def assemble(
        self,
        assembly_input: ContextAssemblyInput,
        items: list[ContextItem],
        policy: TruncationPolicy | None = None,
    ) -> ContextAssemblyResult:
        """Assemble context window from pre-loaded items. Delegates to ContextAssembler."""
        return await self.assembler.assemble(assembly_input, items, policy=policy)

    async def reconstruct(self, snapshot_id: UUID) -> ContextAssemblyResult:
        """
        Replay-safe reconstruction from snapshot ID.
        Raises ContextReplayError if snapshot not found/expired/archived.
        """
        return await self.replay.reconstruct(snapshot_id)

    async def reconstruct_by_key(
        self, assembly_key: str
    ) -> ContextAssemblyResult:
        """
        Replay-safe reconstruction by assembly key.
        Raises ContextReplayError if snapshot not found/expired/archived.
        """
        return await self.replay.reconstruct_by_key(assembly_key)

    def check_budget(
        self,
        level: ContextBudgetLevel,
        actual: int,
        budget: int,
        scope: str | None = None,
    ) -> None:
        """
        Enforce token budget at a specific level.
        Raises ContextBudgetExceededError if actual > budget.
        """
        self._budget.enforce(level, actual, budget, scope=scope)
