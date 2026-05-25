"""
GovernancePolicyRuntime — CRUD + versioning for governance policies.

create(input) — create new policy at version 1 (or next version if key exists).
supersede(policy_key, new_input) — mark old active version superseded, insert new version.
archive(policy_key) — mark active version archived.
get_snapshot(policy_key) — return GovernancePolicySnapshot for replay.
get_all_snapshots() — return all active policy snapshots.
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
from models.governance_policy import GovernancePolicy
from repositories.governance_event import GovernanceEventRepository
from repositories.governance_policy import GovernancePolicyRepository


class PolicyError(Exception):
    pass


class GovernancePolicyRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GovernancePolicyRepository(session)
        self._events = GovernanceEventRepository(session)

    async def create(
        self,
        policy_key: str,
        action_patterns: list[str],
        classification: ActionClassification,
        risk_tier: RiskTier,
        routing_strategy: ApprovalRoutingStrategy = ApprovalRoutingStrategy.direct,
        approver_ids: list[UUID] | None = None,
        escalation_chain: list[dict] | None = None,
        quorum_required: int = 0,
        timeout_seconds: int = 86400,
        escalation_timeout_seconds: int = 3600,
        inherited_from: str | None = None,
        rules: dict | None = None,
        description: str | None = None,
        created_by: UUID | None = None,
    ) -> GovernancePolicy:
        """
        Create a new policy. If policy_key already has an active version, raise.
        """
        existing = await self._repo.get_active_version(policy_key)
        if existing is not None:
            raise PolicyError(
                f"Policy {policy_key!r} already has an active version {existing.version}. "
                "Use supersede() to create a new version."
            )

        latest_version = await self._repo.get_latest_version_number(policy_key)
        version = latest_version + 1

        policy = await self._repo.create(
            policy_key=policy_key,
            version=version,
            status=GovernancePolicyStatus.active,
            action_patterns=action_patterns,
            classification=classification,
            risk_tier=risk_tier,
            routing_strategy=routing_strategy,
            approver_ids=[str(uid) for uid in (approver_ids or [])],
            escalation_chain=escalation_chain or [],
            quorum_required=quorum_required,
            timeout_seconds=timeout_seconds,
            escalation_timeout_seconds=escalation_timeout_seconds,
            inherited_from=inherited_from,
            rules=rules or {},
            description=description,
            created_by=created_by,
        )

        await self._events.append(
            event_type=GovernanceEventType.policy_snapshot_captured,
            policy_id=policy.id,
            actor_id=created_by,
            payload={"policy_key": policy_key, "version": version, "action": "created"},
        )
        return policy

    async def supersede(
        self,
        policy_key: str,
        **new_kwargs,
    ) -> GovernancePolicy:
        """
        Mark current active version superseded, insert new version at version+1.
        """
        current = await self._repo.get_active_version(policy_key)
        if current is None:
            raise PolicyError(f"No active policy found for key {policy_key!r}")

        # Supersede old version
        current.status = GovernancePolicyStatus.superseded
        self._session.add(current)
        await self._session.flush()

        await self._events.append(
            event_type=GovernanceEventType.policy_superseded,
            policy_id=current.id,
            payload={"policy_key": policy_key, "superseded_version": current.version},
        )

        # Create new version
        next_version = current.version + 1
        created_by = new_kwargs.pop("created_by", None)

        new_policy = await self._repo.create(
            policy_key=policy_key,
            version=next_version,
            status=GovernancePolicyStatus.active,
            created_by=created_by,
            **new_kwargs,
        )

        await self._events.append(
            event_type=GovernanceEventType.policy_snapshot_captured,
            policy_id=new_policy.id,
            actor_id=created_by,
            payload={"policy_key": policy_key, "version": next_version, "action": "superseded"},
        )
        return new_policy

    async def archive(self, policy_key: str, actor_id: UUID | None = None) -> GovernancePolicy:
        """Archive the active version of a policy."""
        current = await self._repo.get_active_version(policy_key)
        if current is None:
            raise PolicyError(f"No active policy found for key {policy_key!r}")
        current.status = GovernancePolicyStatus.archived
        self._session.add(current)
        await self._session.flush()
        await self._events.append(
            event_type=GovernanceEventType.policy_superseded,
            policy_id=current.id,
            actor_id=actor_id,
            payload={"policy_key": policy_key, "action": "archived"},
        )
        return current

    def to_snapshot(self, policy: GovernancePolicy) -> GovernancePolicySnapshot:
        """Convert a GovernancePolicy ORM row → GovernancePolicySnapshot."""
        chain = tuple(
            EscalationStep(
                escalate_to=UUID(step["escalate_to"]),
                after_seconds=step["after_seconds"],
                reason=step.get("reason"),
            )
            for step in policy.escalation_chain
        )
        return GovernancePolicySnapshot(
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

    async def get_all_snapshots(self) -> list[GovernancePolicySnapshot]:
        """Return snapshots for all active policies."""
        policies = await self._repo.get_active()
        return [self.to_snapshot(p) for p in policies]

    async def get_snapshot(self, policy_key: str) -> GovernancePolicySnapshot | None:
        """Return snapshot for the active version of policy_key, or None."""
        policy = await self._repo.get_active_version(policy_key)
        return self.to_snapshot(policy) if policy else None
