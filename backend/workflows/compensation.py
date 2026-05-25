"""
Compensating action contract for workflow rollback.

Compensating actions describe side effects that must be undone when a workflow
is rolled back. They are pure data — no execution here. Callers register them;
RollbackCoordinator records them as audit events.

Design constraints:
- Pure data: frozen dataclass, no DB, no side effects
- Replay-safe: re-running coordinator with same actions is idempotent
- Extensible: new action_types added by registering handlers outside this module
- No AI, no orchestration, no policy evaluation

Future action_types (callers implement handlers):
  "cancel_approval"      — void a pending approval on rollback
  "release_lead"         — return lead to unassigned pool
  "void_transcript"      — mark transcript as voided
  "notify_operator"      — queue notification (caller handles send)
  "release_reservation"  — release an external resource hold
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class CompensatingAction:
    """
    A single compensating action to execute on rollback.

    action_type: identifier for the handler (e.g. "cancel_approval")
    target_id:   primary entity being compensated
    payload:     context needed to execute the action
    triggered_by: governance trigger source (e.g. "approval_expired")
    """
    action_type: str
    target_id: UUID
    triggered_by: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RollbackResult:
    """
    Immutable result returned by RollbackCoordinator.coordinate().

    was_idempotent=True means rollback was a no-op (workflow already terminal).
    compensating_actions contains actions recorded as audit events.
    """
    workflow_id: UUID
    trigger: str
    reason: str
    rolled_back_from_step: str | None
    compensating_actions: list[CompensatingAction]
    was_idempotent: bool
