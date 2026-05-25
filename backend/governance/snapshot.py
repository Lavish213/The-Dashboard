"""
GovernancePolicySnapshotRuntime — deterministic policy snapshot capture + replay.

capture(policy_key) — capture current active policy as an immutable snapshot
  and persist it as a governance_event for replay.
replay_snapshots(policy_id) — reconstruct policy history from governance_events.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from governance.contracts import EscalationStep, GovernancePolicySnapshot
from models.enums import (
    ActionClassification,
    ApprovalRoutingStrategy,
    GovernanceEventType,
    GovernancePolicyStatus,
    RiskTier,
)
from repositories.governance_event import GovernanceEventRepository
from repositories.governance_policy import GovernancePolicyRepository


class SnapshotError(Exception):
    pass


class GovernancePolicySnapshotRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._policy_repo = GovernancePolicyRepository(session)
        self._events = GovernanceEventRepository(session)

    async def capture(
        self,
        policy_key: str,
        actor_id: UUID | None = None,
    ) -> GovernancePolicySnapshot:
        """
        Capture the active policy as an immutable snapshot.
        Persists snapshot payload to governance_events for replay.
        """
        policy = await self._policy_repo.get_active_version(policy_key)
        if policy is None:
            raise SnapshotError(f"No active policy for key {policy_key!r}")

        chain = tuple(
            EscalationStep(
                escalate_to=UUID(step["escalate_to"]),
                after_seconds=step["after_seconds"],
                reason=step.get("reason"),
            )
            for step in policy.escalation_chain
        )

        snapshot = GovernancePolicySnapshot(
            snapshot_id=str(uuid4()),
            policy_key=policy.policy_key,
            version=policy.version,
            status=policy.status,
            classification=policy.classification,
            risk_tier=policy.risk_tier,
            action_patterns=tuple(policy.action_patterns),
            routing_strategy=policy.routing_strategy,
            approver_ids=tuple(UUID(uid) for uid in policy.approver_ids),
            escalation_chain=chain,
            quorum_required=policy.quorum_required,
            timeout_seconds=policy.timeout_seconds,
            rules=policy.rules,
            inherited_from=policy.inherited_from,
            captured_at=datetime.now(UTC),
        )

        # Serialize and persist for replay
        payload = {
            "snapshot_id": snapshot.snapshot_id,
            "policy_key": snapshot.policy_key,
            "version": snapshot.version,
            "status": snapshot.status.value,
            "classification": snapshot.classification.value,
            "risk_tier": snapshot.risk_tier.value,
            "action_patterns": list(snapshot.action_patterns),
            "routing_strategy": snapshot.routing_strategy.value,
            "approver_ids": [str(uid) for uid in snapshot.approver_ids],
            "escalation_chain": [
                {
                    "escalate_to": str(step.escalate_to),
                    "after_seconds": step.after_seconds,
                    "reason": step.reason,
                }
                for step in snapshot.escalation_chain
            ],
            "quorum_required": snapshot.quorum_required,
            "timeout_seconds": snapshot.timeout_seconds,
            "rules": snapshot.rules,
            "inherited_from": snapshot.inherited_from,
            "captured_at": snapshot.captured_at.isoformat(),
        }

        await self._events.append(
            event_type=GovernanceEventType.policy_snapshot_captured,
            policy_id=policy.id,
            actor_id=actor_id,
            payload=payload,
        )
        return snapshot

    async def replay_snapshots(self, policy_id: UUID) -> list[GovernancePolicySnapshot]:
        """Reconstruct snapshot history for policy_id from governance_events."""
        events = await self._events.get_for_policy(policy_id)
        snapshots = []
        for evt in events:
            if evt.event_type == GovernanceEventType.policy_snapshot_captured:
                p = evt.payload
                # Only process full snapshots (emitted by capture(), not policy.create())
                if "snapshot_id" not in p or "action_patterns" not in p:
                    continue
                chain = tuple(
                    EscalationStep(
                        escalate_to=UUID(step["escalate_to"]),
                        after_seconds=step["after_seconds"],
                        reason=step.get("reason"),
                    )
                    for step in p.get("escalation_chain", [])
                )
                snapshots.append(
                    GovernancePolicySnapshot(
                        snapshot_id=p["snapshot_id"],
                        policy_key=p["policy_key"],
                        version=p["version"],
                        status=GovernancePolicyStatus(p["status"]),
                        classification=ActionClassification(p["classification"]),
                        risk_tier=RiskTier(p["risk_tier"]),
                        action_patterns=tuple(p["action_patterns"]),
                        routing_strategy=ApprovalRoutingStrategy(p["routing_strategy"]),
                        approver_ids=tuple(UUID(uid) for uid in p.get("approver_ids", [])),
                        escalation_chain=chain,
                        quorum_required=p.get("quorum_required", 0),
                        timeout_seconds=p.get("timeout_seconds", 86400),
                        rules=p.get("rules", {}),
                        inherited_from=p.get("inherited_from"),
                        captured_at=datetime.fromisoformat(p["captured_at"]),
                    )
                )
        return snapshots
