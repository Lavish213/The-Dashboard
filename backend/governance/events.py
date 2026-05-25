"""
GovernanceEnforcementEvents — emit Phase 14 enforcement events.

Thin helpers over GovernanceEventRepository for the three enforcement
event types introduced in Phase 14:

  emit_action_denied      — action blocked by forbidden policy classification
  emit_freeze_propagated  — freeze state blocked a runtime operation
  emit_invariant_violation — runtime invariant was violated

Each function appends one immutable governance_event row.
No business logic. No state mutation beyond event append.
Do not duplicate Phase 11 event emitters (freeze_activated, approval_routed, etc.).
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import GovernanceEventType
from repositories.governance_event import GovernanceEventRepository


async def emit_action_denied(
    session: AsyncSession,
    *,
    action: str,
    classification: str,
    evaluation_id: str,
    scope: str | None = None,
    actor_id: UUID | None = None,
    correlation_id: UUID | None = None,
) -> None:
    """
    Append an action_denied governance event.
    Called when GovernanceEngine.enforce_action() denies a forbidden action.
    """
    repo = GovernanceEventRepository(session)
    await repo.append(
        event_type=GovernanceEventType.action_denied,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "action": action,
            "classification": classification,
            "evaluation_id": evaluation_id,
            "scope": scope,
        },
    )


async def emit_freeze_propagated(
    session: AsyncSession,
    *,
    scope: str,
    source_runtime: str,
    actor_id: UUID | None = None,
    correlation_id: UUID | None = None,
) -> None:
    """
    Append a freeze_propagated governance event.
    Called when GovernanceEngine.check_freeze() blocks a runtime operation.
    """
    repo = GovernanceEventRepository(session)
    await repo.append(
        event_type=GovernanceEventType.freeze_propagated,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "scope": scope,
            "source_runtime": source_runtime,
        },
    )


async def emit_invariant_violation(
    session: AsyncSession,
    *,
    invariant_id: str,
    details: str,
    actor_id: UUID | None = None,
    correlation_id: UUID | None = None,
) -> None:
    """
    Append an invariant_violated governance event.
    Called when a RUNTIME_INVARIANTS.md invariant is detected to be violated.
    """
    repo = GovernanceEventRepository(session)
    await repo.append(
        event_type=GovernanceEventType.invariant_violated,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload={
            "invariant_id": invariant_id,
            "details": details,
        },
    )
