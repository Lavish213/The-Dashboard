"""
DelegationRuntime — approval authority delegation primitives.

grant(delegation_key, delegator_id, delegate_id, ...) — create delegation.
  Idempotent on delegation_key.
revoke(delegation_key, revoke_reason, actor_id) — revoke active delegation.
is_authorized(delegate_id, approval_type, risk_tier) — quick auth check.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from governance.contracts import DelegationGrant
from models.approval_delegation import ApprovalDelegation
from models.enums import ApprovalType, DelegationStatus, GovernanceEventType, RiskTier
from repositories.approval_delegation import ApprovalDelegationRepository
from repositories.governance_event import GovernanceEventRepository


class DelegationError(Exception):
    pass


class DelegationRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ApprovalDelegationRepository(session)
        self._events = GovernanceEventRepository(session)

    async def grant(
        self,
        delegation_key: str,
        delegator_id: UUID,
        delegate_id: UUID,
        approval_types: list[ApprovalType] | None = None,
        risk_tiers: list[RiskTier] | None = None,
        expires_at: datetime | None = None,
        actor_id: UUID | None = None,
    ) -> DelegationGrant:
        """
        Create a delegation. Idempotent on delegation_key — returns existing.
        """
        existing = await self._repo.get_by_key(delegation_key)
        if existing is not None:
            return self._to_grant(existing)

        approval_type_values = [t.value for t in (approval_types or [])]
        risk_tier_values = [r.value for r in (risk_tiers or [])]

        delegation = await self._repo.create(
            delegation_key=delegation_key,
            delegator_id=delegator_id,
            delegate_id=delegate_id,
            approval_types=approval_type_values,
            risk_tiers=risk_tier_values,
            status=DelegationStatus.active,
            expires_at=expires_at,
        )

        await self._events.append(
            event_type=GovernanceEventType.delegation_granted,
            actor_id=actor_id or delegator_id,
            payload={
                "delegation_key": delegation_key,
                "delegator_id": str(delegator_id),
                "delegate_id": str(delegate_id),
                "approval_types": approval_type_values,
                "risk_tiers": risk_tier_values,
                "expires_at": expires_at.isoformat() if expires_at else None,
            },
        )
        return self._to_grant(delegation)

    async def revoke(
        self,
        delegation_key: str,
        revoke_reason: str | None = None,
        actor_id: UUID | None = None,
    ) -> ApprovalDelegation:
        """Revoke an active delegation by key."""
        delegation = await self._repo.get_by_key(delegation_key)
        if delegation is None:
            raise DelegationError(f"Delegation {delegation_key!r} not found")
        if delegation.status != DelegationStatus.active:
            raise DelegationError(
                f"Delegation {delegation_key!r} is not active (status={delegation.status})"
            )

        delegation.status = DelegationStatus.revoked
        delegation.revoked_at = datetime.now(UTC)
        delegation.revoke_reason = revoke_reason
        self._session.add(delegation)
        await self._session.flush()

        await self._events.append(
            event_type=GovernanceEventType.delegation_revoked,
            actor_id=actor_id,
            payload={
                "delegation_key": delegation_key,
                "delegator_id": str(delegation.delegator_id),
                "delegate_id": str(delegation.delegate_id),
                "revoke_reason": revoke_reason,
            },
        )
        return delegation

    async def is_authorized(
        self,
        delegate_id: UUID,
        approval_type: ApprovalType,
        risk_tier: RiskTier,
    ) -> bool:
        """Check if delegate_id has active delegation covering approval_type + risk_tier."""
        delegations = await self._repo.get_active_for_delegate(delegate_id)
        for d in delegations:
            type_ok = not d.approval_types or approval_type.value in d.approval_types
            tier_ok = not d.risk_tiers or risk_tier.value in d.risk_tiers
            if type_ok and tier_ok:
                return True
        return False

    def _to_grant(self, d: ApprovalDelegation) -> DelegationGrant:
        return DelegationGrant(
            delegation_id=d.id,
            delegation_key=d.delegation_key,
            delegator_id=d.delegator_id,
            delegate_id=d.delegate_id,
            approval_types=tuple(d.approval_types),
            risk_tiers=tuple(d.risk_tiers),
            expires_at=d.expires_at,
        )
