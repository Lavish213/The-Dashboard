"""
FreezeRuntime — execution freeze / kill switch infrastructure.

activate(freeze_key, scope, reason, actor_id) — freeze a scope.
deactivate(freeze_key, actor_id) — deactivate a freeze (not kill switches).
kill_switch(freeze_key, scope, reason, actor_id) — permanent freeze, not deactivatable.
is_frozen(scope) — check if scope has an active freeze.

Freeze state is persisted in governance_events (append-only). Deactivation
appends freeze_deactivated. kill_switch appends kill_switch_triggered (permanent).
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from governance.contracts import FreezeSpec
from models.enums import GovernanceEventType
from repositories.governance_event import GovernanceEventRepository


class FreezeError(Exception):
    pass


class FreezeRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = GovernanceEventRepository(session)

    async def activate(
        self,
        freeze_key: str,
        scope: str,
        reason: str,
        actor_id: UUID | None = None,
    ) -> FreezeSpec:
        """Activate a freeze for scope. No-op if already frozen (idempotent)."""
        if await self.is_frozen(scope):
            # Try to reconstruct spec; fall back to a minimal spec if kill-switch frozen
            try:
                return await self._get_spec(scope)
            except FreezeError:
                return FreezeSpec(
                    freeze_key=freeze_key,
                    scope=scope,
                    reason=reason,
                    is_kill_switch=True,
                    activated_by=actor_id,
                    activated_at=datetime.now(UTC),
                )

        now = datetime.now(UTC)
        await self._events.append(
            event_type=GovernanceEventType.freeze_activated,
            actor_id=actor_id,
            payload={
                "freeze_key": freeze_key,
                "scope": scope,
                "reason": reason,
                "is_kill_switch": False,
                "activated_at": now.isoformat(),
            },
        )
        return FreezeSpec(
            freeze_key=freeze_key,
            scope=scope,
            reason=reason,
            is_kill_switch=False,
            activated_by=actor_id,
            activated_at=now,
        )

    async def deactivate(
        self,
        freeze_key: str,
        actor_id: UUID | None = None,
    ) -> None:
        """Deactivate a freeze by key. Raises if it's a kill switch."""
        events = await self._events.get_by_type(GovernanceEventType.freeze_activated)
        for evt in events:
            if evt.payload.get("freeze_key") == freeze_key:
                if evt.payload.get("is_kill_switch"):
                    raise FreezeError(
                        f"Cannot deactivate kill switch {freeze_key!r}"
                    )
        await self._events.append(
            event_type=GovernanceEventType.freeze_deactivated,
            actor_id=actor_id,
            payload={"freeze_key": freeze_key},
        )

    async def kill_switch(
        self,
        freeze_key: str,
        scope: str,
        reason: str,
        actor_id: UUID | None = None,
    ) -> FreezeSpec:
        """Permanently freeze scope. Cannot be deactivated."""
        now = datetime.now(UTC)
        await self._events.append(
            event_type=GovernanceEventType.kill_switch_triggered,
            actor_id=actor_id,
            payload={
                "freeze_key": freeze_key,
                "scope": scope,
                "reason": reason,
                "is_kill_switch": True,
                "activated_at": now.isoformat(),
            },
        )
        return FreezeSpec(
            freeze_key=freeze_key,
            scope=scope,
            reason=reason,
            is_kill_switch=True,
            activated_by=actor_id,
            activated_at=now,
        )

    async def is_frozen(self, scope: str) -> bool:
        """
        Return True if scope has an active freeze or kill switch.

        A freeze_activated event is active unless a later freeze_deactivated
        event exists for the same freeze_key. Kill switches are always active.
        """
        activated: dict[str, dict] = {}
        deactivated: set[str] = set()

        freeze_events = await self._events.get_by_type(GovernanceEventType.freeze_activated)
        kill_events = await self._events.get_by_type(GovernanceEventType.kill_switch_triggered)
        deact_events = await self._events.get_by_type(GovernanceEventType.freeze_deactivated)

        for evt in kill_events:
            if evt.payload.get("scope") == scope:
                return True  # kill switch always active

        for evt in freeze_events:
            if evt.payload.get("scope") == scope:
                activated[evt.payload["freeze_key"]] = evt.payload

        for evt in deact_events:
            deactivated.add(evt.payload.get("freeze_key", ""))

        for freeze_key, payload in activated.items():
            if freeze_key not in deactivated:
                return True
        return False

    async def _get_spec(self, scope: str) -> FreezeSpec:
        """Reconstruct FreezeSpec for an active freeze on scope."""
        events = await self._events.get_by_type(GovernanceEventType.freeze_activated)
        deact_events = await self._events.get_by_type(GovernanceEventType.freeze_deactivated)
        deactivated = {e.payload.get("freeze_key", "") for e in deact_events}

        for evt in reversed(events):
            if evt.payload.get("scope") == scope:
                fk = evt.payload["freeze_key"]
                if fk not in deactivated:
                    return FreezeSpec(
                        freeze_key=fk,
                        scope=scope,
                        reason=evt.payload["reason"],
                        is_kill_switch=evt.payload.get("is_kill_switch", False),
                        activated_by=evt.actor_id,
                        activated_at=datetime.fromisoformat(evt.payload["activated_at"]),
                    )
        raise FreezeError(f"No active freeze found for scope {scope!r}")
