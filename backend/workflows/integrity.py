"""
ExecutionIntegrityRuntime — deterministic execution health sweep.

Single entry point for the background integrity worker. Runs:
1. Stale lease expiry
2. Orphaned workflow detection + recovery
3. Stalled workflow detection + advisory events

Errors in individual steps are captured and reported — sweep continues.
Emits EVT_INTEGRITY_SWEEP domain event on completion for replay audit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from events.contracts import DomainEvent
from events.emitter import event_emitter
from workflows.lease import LeaseRuntime
from workflows.orphaned import OrphanedRecovery
from workflows.stalled import DEFAULT_MAX_IDLE_SECONDS, StalledDetector

logger = structlog.get_logger(__name__)

INTEGRITY_CHANNEL = "workflows"
EVT_INTEGRITY_SWEEP = "workflow.integrity.sweep_completed"


@dataclass
class IntegritySweepResult:
    swept_at: datetime
    expired_leases: list[UUID] = field(default_factory=list)
    orphaned_detected: int = 0
    orphaned_recovered: int = 0
    orphaned_cancelled: int = 0
    stalled_detected: int = 0
    errors: list[str] = field(default_factory=list)


class ExecutionIntegrityRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._lease = LeaseRuntime(session)
        self._orphaned = OrphanedRecovery(session)
        self._stalled = StalledDetector(session)

    async def run_integrity_sweep(
        self,
        max_idle_seconds: int = DEFAULT_MAX_IDLE_SECONDS,
    ) -> IntegritySweepResult:
        """
        Run full integrity sweep. Errors are collected, not raised.
        Returns IntegritySweepResult with counts and any non-fatal errors.
        """
        result = IntegritySweepResult(swept_at=datetime.now(UTC))

        # 1. Expire stale leases
        try:
            result.expired_leases = await self._lease.expire_stale()
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"lease_expiry: {exc}")

        # 2. Orphaned recovery (only workflows with expired leases)
        try:
            orphaned = await self._orphaned.find_orphaned()
            result.orphaned_detected = len(orphaned)
            for o in orphaned:
                try:
                    recovered = await self._orphaned.recover(o.workflow_id)
                    if recovered is not None:
                        result.orphaned_recovered += 1
                    else:
                        result.orphaned_cancelled += 1
                except Exception as exc:  # noqa: BLE001
                    result.errors.append(f"orphan_recover_{o.workflow_id}: {exc}")
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"orphan_detection: {exc}")

        # 3. Stalled detection (advisory — no state mutations)
        try:
            stalled = await self._stalled.find_stalled(max_idle_seconds=max_idle_seconds)
            result.stalled_detected = len(stalled)
            for s in stalled:
                try:
                    await self._stalled.mark_stalled(s.workflow_id, s.stalled_for_seconds)
                except Exception as exc:  # noqa: BLE001
                    result.errors.append(f"stall_mark_{s.workflow_id}: {exc}")
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"stall_detection: {exc}")

        await event_emitter.emit(
            self._session,
            DomainEvent(
                channel=INTEGRITY_CHANNEL,
                event_type=EVT_INTEGRITY_SWEEP,
                payload={
                    "swept_at": result.swept_at.isoformat(),
                    "expired_leases": len(result.expired_leases),
                    "orphaned_detected": result.orphaned_detected,
                    "orphaned_recovered": result.orphaned_recovered,
                    "stalled_detected": result.stalled_detected,
                    "errors": result.errors,
                },
            ),
        )

        logger.info(
            "integrity.sweep",
            expired_leases=len(result.expired_leases),
            orphaned=result.orphaned_detected,
            recovered=result.orphaned_recovered,
            stalled=result.stalled_detected,
        )

        return result
