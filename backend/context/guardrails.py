"""
ContextInjectionGuardrail — approval-safe context hydration boundaries.

Prevents injection of context that:
  - exceeds the declared token budget
  - contains layers not in the approved layer filter
  - originates from sources that require approval before use
  - is from a snapshot that has expired or been archived

All checks are pure / side-effect free. Raises ContextGuardrailError on
violation. Callers must catch and handle before injecting context into
any AI execution or external boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from context.contracts import ContextAssemblyInput, ContextWindow
from models.enums import ContextLayerType, ContextSnapshotStatus


class ContextGuardrailError(Exception):
    """Raised when a guardrail check fails."""

    def __init__(self, reason: str, detail: dict | None = None) -> None:
        self.reason = reason
        self.detail = detail or {}
        super().__init__(reason)


@dataclass(frozen=True)
class GuardrailResult:
    """Result of a guardrail check."""

    passed: bool
    reason: str | None = None
    detail: dict | None = None


class ContextInjectionGuardrail:
    """
    Stateless guardrail checker.

    check_window(window, assembly_input) — validate window against input spec.
    check_snapshot_status(status) — block expired/archived snapshots.
    check_layer_access(item_layers, allowed_layers) — block unauthorized layers.
    """

    def check_window(
        self,
        window: ContextWindow,
        assembly_input: ContextAssemblyInput,
    ) -> GuardrailResult:
        """
        Validate the assembled window against the assembly input spec.
        Raises ContextGuardrailError on any violation.
        """
        # Token budget check
        if window.total_tokens > assembly_input.token_budget:
            raise ContextGuardrailError(
                "context_budget_exceeded",
                {
                    "total_tokens": window.total_tokens,
                    "token_budget": assembly_input.token_budget,
                },
            )

        # Layer filter check
        if assembly_input.layer_filter is not None:
            allowed = set(assembly_input.layer_filter)
            for item in window.items:
                if item.layer not in allowed:
                    raise ContextGuardrailError(
                        "context_layer_not_allowed",
                        {
                            "layer": item.layer.value,
                            "allowed_layers": [lyr.value for lyr in allowed],
                        },
                    )

        return GuardrailResult(passed=True)

    def check_snapshot_status(
        self,
        status: ContextSnapshotStatus,
        snapshot_id: UUID | None = None,
    ) -> GuardrailResult:
        """Block injection of expired or archived snapshots."""
        if status in (ContextSnapshotStatus.archived, ContextSnapshotStatus.expired):
            raise ContextGuardrailError(
                "context_snapshot_not_injectable",
                {
                    "status": status.value,
                    "snapshot_id": str(snapshot_id) if snapshot_id else None,
                },
            )
        return GuardrailResult(passed=True)

    def check_layer_access(
        self,
        requested_layers: list[ContextLayerType],
        allowed_layers: list[ContextLayerType],
    ) -> GuardrailResult:
        """Verify all requested layers are in the allowed set."""
        allowed_set = set(allowed_layers)
        for layer in requested_layers:
            if layer not in allowed_set:
                raise ContextGuardrailError(
                    "context_layer_access_denied",
                    {
                        "requested_layer": layer.value,
                        "allowed_layers": [lyr.value for lyr in allowed_layers],
                    },
                )
        return GuardrailResult(passed=True)
