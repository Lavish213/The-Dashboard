"""
ContextSnapshotRuntime — persist and restore assembled context snapshots.

create(assembly_input, window, provenance) — persist new snapshot.
  Returns ContextAssemblyResult. Idempotent on assembly_key.

restore(snapshot_id) — reconstruct ContextAssemblyResult from DB row.
restore_by_key(assembly_key) — same, by idempotency key.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from context.contracts import (
    ContextAssemblyInput,
    ContextAssemblyResult,
    ContextWindow,
)
from context.provenance import ContextProvenanceTracker
from models.enums import ContextLayerType, ContextSnapshotStatus, ContextWindowStrategy
from repositories.context_snapshot import ContextSnapshotRepository

_provenance_tracker = ContextProvenanceTracker()


class ContextSnapshotRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ContextSnapshotRepository(session)

    async def create(
        self,
        assembly_input: ContextAssemblyInput,
        window: ContextWindow,
        provenance: dict,
    ) -> ContextAssemblyResult:
        """
        Persist an assembled context window as a snapshot.
        Idempotent: if assembly_key already exists, return existing.
        """
        existing = await self._repo.get_by_key(assembly_input.assembly_key)
        if existing is not None:
            return self._to_result(existing, from_cache=True)

        window_payload = {
            "items": [
                {
                    "layer": item.layer.value,
                    "source_id": str(item.source_id),
                    "source_type": item.source_type,
                    "content": item.content,
                    "token_count": item.token_count,
                    "priority": item.priority,
                    "metadata": item.metadata,
                }
                for item in window.items
            ],
            "total_tokens": window.total_tokens,
            "truncated": window.truncated,
            "truncated_count": window.truncated_count,
            "strategy": window.strategy.value,
        }

        layer_types = list(
            dict.fromkeys(item.layer.value for item in window.items)
        )

        assembly_params = {
            "token_budget": assembly_input.token_budget,
            "strategy": assembly_input.strategy.value,
            "layer_filter": (
                [lyr.value for lyr in assembly_input.layer_filter]
                if assembly_input.layer_filter
                else None
            ),
        }

        snapshot = await self._repo.create(
            assembly_key=assembly_input.assembly_key,
            status=ContextSnapshotStatus.active,
            workflow_id=assembly_input.workflow_id,
            transcript_id=assembly_input.transcript_id,
            execution_id=assembly_input.execution_id,
            actor_id=assembly_input.actor_id,
            token_count=window.total_tokens,
            token_budget=assembly_input.token_budget,
            layer_types=layer_types,
            window_payload=window_payload,
            provenance=provenance,
            assembly_params=assembly_params,
        )

        return ContextAssemblyResult(
            snapshot_id=snapshot.id,
            assembly_key=assembly_input.assembly_key,
            window=window,
            provenance=provenance,
            from_cache=False,
        )

    async def restore(self, snapshot_id: UUID) -> ContextAssemblyResult | None:
        """Reconstruct ContextAssemblyResult from a persisted snapshot."""
        snapshot = await self._repo.get_by_id(snapshot_id)
        if snapshot is None:
            return None
        return self._to_result(snapshot)

    async def restore_by_key(self, assembly_key: str) -> ContextAssemblyResult | None:
        """Reconstruct ContextAssemblyResult by assembly_key."""
        snapshot = await self._repo.get_by_key(assembly_key)
        if snapshot is None:
            return None
        return self._to_result(snapshot)

    def _to_result(self, snapshot, from_cache: bool = False) -> ContextAssemblyResult:
        """Deserialize snapshot row → ContextAssemblyResult."""
        from context.contracts import ContextItem

        payload = snapshot.window_payload
        items = tuple(
            ContextItem(
                layer=ContextLayerType(i["layer"]),
                source_id=UUID(i["source_id"]),
                source_type=i["source_type"],
                content=i["content"],
                token_count=i["token_count"],
                priority=i["priority"],
                metadata=i.get("metadata", {}),
            )
            for i in payload.get("items", [])
        )

        window = ContextWindow(
            items=items,
            total_tokens=payload.get("total_tokens", 0),
            token_budget=snapshot.token_budget,
            truncated=payload.get("truncated", False),
            truncated_count=payload.get("truncated_count", 0),
            strategy=ContextWindowStrategy(
                payload.get("strategy", ContextWindowStrategy.truncate_oldest.value)
            ),
        )

        return ContextAssemblyResult(
            snapshot_id=snapshot.id,
            assembly_key=snapshot.assembly_key,
            window=window,
            provenance=snapshot.provenance,
            from_cache=from_cache,
        )
