"""
ContextProvenanceTracker — immutable source attribution for assembled context.

Tracks which domain entities contributed context items, how many items
each contributed, and how many tokens. Used for forensic reconstruction
and audit linkage.

All operations are pure / side-effect free — no DB writes.
"""
from __future__ import annotations

from uuid import UUID

from context.contracts import ContextItem, ContextProvenance


class ContextProvenanceTracker:
    """
    Build immutable provenance records from assembled context items.

    build(items) → dict[str, ContextProvenance]
      Key: "<source_type>:<source_id>"
    """

    def build(self, items: list[ContextItem]) -> dict[str, ContextProvenance]:
        """
        Aggregate ContextProvenance per source from a list of ContextItems.

        Returns a mapping keyed by "<source_type>:<source_id>" for deterministic
        serialization and lookup.
        """
        accumulated: dict[str, dict] = {}

        for item in items:
            key = f"{item.source_type}:{item.source_id}"
            if key not in accumulated:
                accumulated[key] = {
                    "source_id": item.source_id,
                    "source_type": item.source_type,
                    "layer": item.layer,
                    "item_count": 0,
                    "token_count": 0,
                }
            accumulated[key]["item_count"] += 1
            accumulated[key]["token_count"] += item.token_count

        return {
            key: ContextProvenance(
                source_id=v["source_id"],
                source_type=v["source_type"],
                layer=v["layer"],
                item_count=v["item_count"],
                token_count=v["token_count"],
            )
            for key, v in accumulated.items()
        }

    def serialize(self, provenance: dict[str, ContextProvenance]) -> dict:
        """
        Serialize provenance map to a JSON-safe dict for persistence.
        """
        return {
            key: {
                "source_id": str(p.source_id),
                "source_type": p.source_type,
                "layer": p.layer.value,
                "item_count": p.item_count,
                "token_count": p.token_count,
            }
            for key, p in provenance.items()
        }

    def deserialize(self, raw: dict) -> dict[str, ContextProvenance]:
        """
        Reconstruct provenance map from persisted JSON dict.
        """
        from models.enums import ContextLayerType

        return {
            key: ContextProvenance(
                source_id=UUID(v["source_id"]),
                source_type=v["source_type"],
                layer=ContextLayerType(v["layer"]),
                item_count=v["item_count"],
                token_count=v["token_count"],
            )
            for key, v in raw.items()
        }
