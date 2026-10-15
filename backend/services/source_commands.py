import asyncio
import hashlib
import json
import os
from copy import deepcopy
from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import UUID

import httpx
import structlog
from fastapi import HTTPException
from sqlalchemy import cast, func, literal, select
from sqlalchemy.dialects.postgresql import JSONB, JSONPATH

from db.session import async_session_factory
from models.lead import Lead
from services.business_evidence import business_from_lead

logger = structlog.get_logger(__name__)


def destination():
    url = os.environ.get("REI_COMMAND_URL", "").rstrip("/")
    secret = os.environ.get("SOURCE_COMMAND_SECRET", "")
    parsed = urlsplit(url)
    if (
        len(secret) < 32
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or parsed.scheme not in {"http", "https"}
        or (
            parsed.scheme == "http"
            and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        )
    ):
        raise HTTPException(503, "Verified source command transport is not configured")
    target = hashlib.sha256(
        (url + ":" + hashlib.sha256(secret.encode()).hexdigest()).encode()
    ).hexdigest()
    return url, secret, target


async def locked_source_lead(session, lead_id):
    lead = await session.scalar(
        select(Lead).where(Lead.id == lead_id, Lead.deleted_at.is_(None))
    )
    external = (lead.metadata_ or {}).get("external_lead_id") if lead else None
    if (
        not isinstance(external, str)
        or (lead.metadata_ or {}).get("external_source") != "rei"
    ):
        raise HTTPException(409, "Canonical source lead required")
    await session.execute(
        select(
            func.pg_advisory_xact_lock(func.hashtextextended("rei-lead:" + external, 0))
        )
    )
    lead = await session.scalar(
        select(Lead)
        .where(Lead.id == lead_id, Lead.deleted_at.is_(None))
        .execution_options(populate_existing=True)
    )
    if lead is None or (lead.metadata_ or {}).get("external_lead_id") != external:
        raise HTTPException(409, "Source identity changed")
    return lead


async def stage_callback(session, lead_id, request_id, at, revision, actor_id):
    return await _stage_command(session, lead_id, request_id, revision, actor_id, at=at)


async def stage_operation(session, lead_id, request_id, revision, actor_id, action, data, reason):
    if not isinstance(reason, str) or not 10 <= len(reason.strip()) <= 1000 or not isinstance(data, dict):
        raise HTTPException(422, "Explicit operation and review reason required")
    if action == "set_disposition":
        if set(data) != {"disposition"} or data["disposition"] not in {"HOT", "WARM", "COLD", "DEAD"}:
            raise HTTPException(422, "Valid disposition required")
    elif action == "cancel_walkthrough":
        if set(data) != {"starts_at"}:
            raise HTTPException(422, "Exact reservation required")
        try:
            if datetime.fromisoformat(data['starts_at'].replace('Z', '+00:00')).tzinfo is None:
                raise ValueError('Timezone required')
        except (ValueError, TypeError, AttributeError) as error:
            raise HTTPException(422, "Exact timezone-aware reservation required") from error
    elif action == "draft_offer":
        if set(data) != {"amount_cents", "repair_cents", "arv_cents"}:
            raise HTTPException(422, "Explicit draft money required")
        for key, value in data.items():
            if key == "arv_cents" and value is None:
                continue
            if type(value) is not int or not 0 <= value <= 10**14 or (key != "repair_cents" and value == 0):
                raise HTTPException(422, "Bounded integer cents required")
    else:
        raise HTTPException(422, "Unsupported source operation")
    return await _stage_command(session, lead_id, request_id, revision, actor_id, action=action, detail=data, reason=reason.strip())


async def _stage_command(session, lead_id, request_id, revision, actor_id, at=None, action="schedule_callback", detail=None, reason=None):
    _, _, target = destination()
    lead = await locked_source_lead(session, lead_id)
    evidence = business_from_lead(lead)
    snapshot = evidence.get("snapshot") or {}
    if evidence.get("status") != "current" or revision != evidence.get("revision"):
        raise HTTPException(409, "Refresh source evidence before scheduling")
    if action == "schedule_callback" and (
        at.tzinfo is None
        or not 0 < (at - datetime.now(UTC)).total_seconds() <= 90 * 86400
    ):
        raise HTTPException(422, "Future timezone-aware callback required")
    payload = {
        "id": str(request_id),
        "tenant_id": snapshot.get("tenant_id"),
        "lead_id": lead.metadata_["external_lead_id"],
        "property_id": snapshot.get("property_id"),
        "expected_updated_at": snapshot.get("source_updated_at"),
    }
    if action == "schedule_callback":
        payload["at"] = at.astimezone(UTC).isoformat()
    else:
        if action == "cancel_walkthrough":
            appointment = snapshot.get("appointment") or {}
            if appointment.get("status") != "confirmed" or appointment.get("at") != detail["starts_at"]:
                raise HTTPException(409, "Refresh the confirmed source reservation")
        payload.update({"action": action, "data": detail, "actor_id": str(actor_id), "reason": reason})
    try:
        for key in ("tenant_id", "lead_id", "property_id"):
            UUID(payload[key])
        if (
            datetime.fromisoformat(
                payload["expected_updated_at"].replace("Z", "+00:00")
            ).tzinfo
            is None
        ):
            raise ValueError("Timezone required")
    except (ValueError, TypeError, AttributeError) as error:
        raise HTTPException(
            409, "Source version and identities require refresh"
        ) from error
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()
    metadata = deepcopy(lead.metadata_ or {})
    commands = dict(metadata.get("source_commands") or {})
    existing = commands.get(str(request_id))
    if existing:
        if existing["fingerprint"] != fingerprint or existing["target"] != target:
            raise HTTPException(409, "Conflicting command replay")
        return {"id": str(request_id), "state": existing["state"], "duplicate": True}
    if len(commands) >= 100:
        raise HTTPException(409, "Source command review budget exhausted")
    commands[str(request_id)] = {
        "payload": payload,
        "action": action,
        "fingerprint": fingerprint,
        "target": target,
        "state": "pending",
        "actor_id": str(actor_id),
        "created_at": datetime.now(UTC).isoformat(),
        "attempts": 0,
    }
    metadata["source_commands"] = commands
    lead.metadata_ = metadata
    await session.commit()
    return {"id": str(request_id), "state": "pending", "duplicate": False}


async def recover_commands(limit=20):
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("Bounded command recovery required")
    url, secret, target = destination()
    async with async_session_factory() as session:
        leads = (
            await session.scalars(
                select(Lead)
                .where(
                    Lead.deleted_at.is_(None),
                    func.jsonb_path_exists(
                        cast(Lead.metadata_, JSONB),
                        cast(
                            literal('$.source_commands.* ? (@.state == "pending")'),
                            JSONPATH,
                        ),
                    ),
                )
                .order_by(Lead.updated_at, Lead.id)
                .limit(limit)
            )
        ).all()
        identities = [lead.id for lead in leads]
    for identity in identities:
        async with async_session_factory() as session:
            lead = await locked_source_lead(session, identity)
            metadata = deepcopy(lead.metadata_ or {})
            commands = dict(metadata.get("source_commands") or {})
            attempts_this_lead = 0
            for key, command in commands.items():
                if command["state"] != "pending":
                    continue
                if command["target"] != target:
                    command["state"] = "requires_review"
                    command["error"] = "destination_changed"
                    continue
                if (
                    datetime.now(UTC) - datetime.fromisoformat(command["created_at"])
                ).total_seconds() > 86400 or command["attempts"] >= 30:
                    command["state"] = "requires_review"
                    command["error"] = "retry_budget_exhausted"
                    continue
                if attempts_this_lead >= 1:
                    break
                attempts_this_lead += 1
                command["attempts"] += 1
                try:
                    action = command.get("action", "schedule_callback")
                    if action not in {"schedule_callback", "set_disposition", "cancel_walkthrough", "draft_offer"}:
                        command["state"] = "requires_review"
                        command["error"] = "unsupported_operation"
                        continue
                    endpoint = "/api/operations/callback" if action == "schedule_callback" else "/api/operations/command"
                    async with httpx.AsyncClient(
                        timeout=5, follow_redirects=False
                    ) as client:
                        response = await client.post(
                            url + endpoint,
                            json=command["payload"],
                            headers={"X-Source-Command-Secret": secret},
                        )
                    receipt = response.json() if response.is_success else {}
                    if (
                        receipt.get("schema_version") == 1
                        and receipt.get("persisted") is True
                        and receipt.get("receipt_id") == key
                        and receipt.get("lead_id") == command["payload"]["lead_id"]
                        and receipt.get("action") == action
                    ):
                        command["state"] = "applied"
                        command["receipt"] = receipt
                    elif response.status_code in {400, 401, 403, 409, 422}:
                        command["state"] = "requires_review"
                        command["error"] = "source_rejected"
                    else:
                        command["error"] = "unconfirmed_source_receipt"
                except Exception as error:
                    command["error"] = type(error).__name__
            metadata["source_commands"] = commands
            lead.metadata_ = metadata
            await session.commit()


async def recovery_loop():
    while True:
        try:
            await recover_commands()
        except Exception as error:
            logger.warning(
                "source_command_recovery_unavailable", error_type=type(error).__name__
            )
        await asyncio.sleep(30)


async def command_status(session, lead_id):
    lead = await session.scalar(
        select(Lead).where(Lead.id == lead_id, Lead.deleted_at.is_(None))
    )
    if lead is None:
        raise HTTPException(404, "Lead not found")
    return {
        "items": [
            {
                "id": identity,
                "state": command.get("state"),
                "action": command.get("action", "schedule_callback"),
                "at": (command.get("payload") or {}).get("at"),
                "created_at": command.get("created_at"),
                "error": command.get("error"),
            }
            for identity, command in (
                (lead.metadata_ or {}).get("source_commands") or {}
            ).items()
        ]
    }
