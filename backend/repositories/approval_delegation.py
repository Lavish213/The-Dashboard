"""ApprovalDelegationRepository — data access for approval_delegations."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.approval_delegation import ApprovalDelegation
from models.enums import DelegationStatus
from repositories.base import BaseRepository


class ApprovalDelegationRepository(BaseRepository[ApprovalDelegation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ApprovalDelegation)

    async def get_by_key(self, delegation_key: str) -> ApprovalDelegation | None:
        result = await self.session.execute(
            select(ApprovalDelegation).where(
                ApprovalDelegation.delegation_key == delegation_key
            )
        )
        return result.scalar_one_or_none()

    async def get_active_for_delegate(self, delegate_id: UUID) -> list[ApprovalDelegation]:
        """Return active (non-expired) delegations for a delegate."""
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(ApprovalDelegation).where(
                ApprovalDelegation.delegate_id == delegate_id,
                ApprovalDelegation.status == DelegationStatus.active,
                (
                    ApprovalDelegation.expires_at.is_(None)
                    | (ApprovalDelegation.expires_at > now)
                ),
            )
        )
        return list(result.scalars().all())

    async def get_active_for_delegator(self, delegator_id: UUID) -> list[ApprovalDelegation]:
        """Return active delegations granted by a delegator."""
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(ApprovalDelegation).where(
                ApprovalDelegation.delegator_id == delegator_id,
                ApprovalDelegation.status == DelegationStatus.active,
                (
                    ApprovalDelegation.expires_at.is_(None)
                    | (ApprovalDelegation.expires_at > now)
                ),
            )
        )
        return list(result.scalars().all())
