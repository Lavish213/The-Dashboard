"""
ContextAssembler — deterministic, bounded context assembly.

Orchestrates adapters → window → provenance → snapshot → audit.

assemble(assembly_input, items) → ContextAssemblyResult

Flow:
  1. Apply layer filter to items.
  2. Build ContextWindow via ContextWindowRuntime (pure, no I/O).
  3. Run guardrail check.
  4. Build provenance map.
  5. Persist snapshot (idempotent on assembly_key).
  6. Check cache — if hit, return cached result.
  7. Record audit entry.
  8. Store result in cache.
  9. Return ContextAssemblyResult.

The assembler is stateless beyond injected dependencies.
All determinism comes from ordered inputs and pure window building.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from context.audit import (
    ACTION_ASSEMBLY_COMPLETED,
    ACTION_CACHE_HIT,
    ContextAuditRuntime,
)
from context.cache import ContextCacheRuntime
from context.contracts import (
    ContextAssemblyInput,
    ContextAssemblyResult,
    ContextItem,
    TruncationPolicy,
)
from context.guardrails import ContextInjectionGuardrail
from context.provenance import ContextProvenanceTracker
from context.snapshot import ContextSnapshotRuntime
from context.window import ContextWindowRuntime

_window_runtime = ContextWindowRuntime()
_guardrail = ContextInjectionGuardrail()
_prov_tracker = ContextProvenanceTracker()

# Module-level cache shared across assembler instances in the same process
_cache = ContextCacheRuntime()


class ContextAssembler:
    """
    Main entry point for context assembly.

    inject dependencies via constructor for testability.
    """

    def __init__(
        self,
        session: AsyncSession,
        cache: ContextCacheRuntime | None = None,
    ) -> None:
        self._session = session
        self._snapshot_rt = ContextSnapshotRuntime(session)
        self._audit_rt = ContextAuditRuntime(session)
        self._cache = cache if cache is not None else _cache

    async def assemble(
        self,
        assembly_input: ContextAssemblyInput,
        items: list[ContextItem],
        policy: TruncationPolicy | None = None,
    ) -> ContextAssemblyResult:
        """
        Assemble a bounded context window from items and persist a snapshot.

        items: pre-loaded ContextItems from adapters.
        policy: truncation policy (defaults to strategy from assembly_input).
        """
        # Cache check — return immediately on hit
        cached = self._cache.get(assembly_input.assembly_key)
        if cached is not None:
            await self._audit_rt.record(
                action=ACTION_CACHE_HIT,
                payload={"assembly_key": assembly_input.assembly_key},
                actor_id=assembly_input.actor_id,
            )
            from dataclasses import replace
            return replace(cached, from_cache=True)

        # Apply layer filter
        if assembly_input.layer_filter is not None:
            allowed = set(assembly_input.layer_filter)
            filtered_items = [i for i in items if i.layer in allowed]
        else:
            filtered_items = list(items)

        # Build truncation policy from assembly_input if not provided
        if policy is None:
            from models.enums import ContextLayerType
            policy = TruncationPolicy(
                strategy=assembly_input.strategy,
                protect_layers=(ContextLayerType.system,),
            )

        # Build bounded window (pure, no I/O)
        window = _window_runtime.build(filtered_items, assembly_input.token_budget, policy)

        # Guardrail check
        _guardrail.check_window(window, assembly_input)

        # Build provenance
        prov_map = _prov_tracker.build(list(window.items))
        prov_serialized = _prov_tracker.serialize(prov_map)

        # Persist snapshot (idempotent)
        result = await self._snapshot_rt.create(assembly_input, window, prov_serialized)

        # Audit
        await self._audit_rt.record(
            action=ACTION_ASSEMBLY_COMPLETED,
            snapshot_id=result.snapshot_id,
            payload={
                "assembly_key": assembly_input.assembly_key,
                "total_tokens": window.total_tokens,
                "item_count": len(window.items),
                "truncated": window.truncated,
                "from_cache": result.from_cache,
            },
            actor_id=assembly_input.actor_id,
        )

        # Cache result
        self._cache.set(assembly_input.assembly_key, result)

        return result
