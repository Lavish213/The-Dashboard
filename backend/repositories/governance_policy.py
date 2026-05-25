"""GovernancePolicyRepository — data access for governance_policies."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import GovernancePolicyStatus
from models.governance_policy import GovernancePolicy
from repositories.base import BaseRepository


class GovernancePolicyRepository(BaseRepository[GovernancePolicy]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GovernancePolicy)

    async def get_active(self) -> list[GovernancePolicy]:
        """Return all active policies."""
        result = await self.session.execute(
            select(GovernancePolicy).where(
                GovernancePolicy.status == GovernancePolicyStatus.active
            )
        )
        return list(result.scalars().all())

    async def get_by_key(self, policy_key: str) -> list[GovernancePolicy]:
        """Return all versions for a policy_key, newest first."""
        result = await self.session.execute(
            select(GovernancePolicy)
            .where(GovernancePolicy.policy_key == policy_key)
            .order_by(GovernancePolicy.version.desc())
        )
        return list(result.scalars().all())

    async def get_active_version(self, policy_key: str) -> GovernancePolicy | None:
        """Return the current active version for a policy_key."""
        result = await self.session.execute(
            select(GovernancePolicy).where(
                GovernancePolicy.policy_key == policy_key,
                GovernancePolicy.status == GovernancePolicyStatus.active,
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_version_number(self, policy_key: str) -> int:
        """Return the highest version number for policy_key (0 if none)."""
        rows = await self.get_by_key(policy_key)
        return rows[0].version if rows else 0
