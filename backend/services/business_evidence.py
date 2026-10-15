import hashlib
import json
from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select

from models.lead import Lead
from services.voice_ingest import find_call, resolve_lead


def validate_snapshot(body):
    snapshot = body.get("snapshot")
    if (
        not isinstance(snapshot, dict)
        or snapshot.get("schema_version") != 1
        or type(snapshot.get("schema_version")) is not int
        or snapshot.get("quote_authorized") is not False
        or snapshot.get("offer_authorized") is not False
    ):
        raise HTTPException(422, "Invalid advisory business snapshot")
    if (
        not isinstance(snapshot.get("property_id"), str)
        or not snapshot["property_id"]
        or len(snapshot["property_id"]) > 255
    ):
        raise HTTPException(422, "Property identity required")
    if (
        len(json.dumps(snapshot)) > 100000
        or not isinstance(snapshot.get("comparables"), list)
        or len(snapshot["comparables"]) > 50
        or not isinstance(snapshot.get("offers"), list)
        or len(snapshot["offers"]) > 20
        or not isinstance(snapshot.get("appointment"), dict)
    ):
        raise HTTPException(422, "Snapshot collection budget exceeded")
    for row in snapshot["comparables"]:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("source_ref"), str)
            or not 0 < len(row["source_ref"]) <= 500
        ):
            raise HTTPException(422, "Comparable source reference required")
        for key in ("sale_price_cents", "adjusted_value_cents"):
            value = row.get(key)
            if value is not None and (
                type(value) is not int or not 0 <= value <= 10**14
            ):
                raise HTTPException(422, "Comparable amounts must be integer cents")
    for row in snapshot["offers"]:
        if not isinstance(row, dict) or row.get("status") not in {
            "draft",
            "sent",
            "countered",
            "accepted",
            "rejected",
            "expired",
        }:
            raise HTTPException(422, "Invalid offer record")
        for key in ("amount_cents", "repairs_cents"):
            value = row.get(key)
            if value is not None and (
                type(value) is not int or not 0 <= value <= 10**14
            ):
                raise HTTPException(422, "Offer amounts must be integer cents")
    appointment = snapshot["appointment"]
    if appointment.get("status") is not None and appointment["status"] not in {
        "confirmed",
        "cancelled",
        "scheduled",
        "pending",
        "completed",
        "missed",
    }:
        raise HTTPException(422, "Invalid appointment status")
    if appointment.get("at") is not None:
        try:
            slot = datetime.fromisoformat(appointment["at"].replace("Z", "+00:00"))
            if slot.tzinfo is None:
                raise ValueError("Timezone required")
        except (ValueError, TypeError, AttributeError) as error:
            raise HTTPException(
                422, "Appointment requires a dated time with UTC offset"
            ) from error
    elif appointment.get("status") in {"confirmed", "scheduled"}:
        raise HTTPException(422, "Confirmed appointment requires a time")
    valuation = snapshot.get("valuation")
    if valuation is not None:
        if (
            not isinstance(valuation, dict)
            or valuation.get("lead_id") != body.get("lead_id")
            or valuation.get("status") != "ready_advisory"
            or valuation.get("method") != "evidence_adjusted_sales_comparison"
            or valuation.get("purpose") not in {"as_is", "after_repair"}
            or valuation.get("quote_authorized") is not False
            or valuation.get("offer_authorized") is not False
        ):
            raise HTTPException(422, "Invalid bound research valuation")
        for row in snapshot["comparables"]:
            if (
                type(row.get("sale_price_cents")) is not int
                or not 0 < row["sale_price_cents"] <= 10**14
                or type(row.get("adjusted_value_cents")) is not int
                or not 0 < row["adjusted_value_cents"] <= 10**14
            ):
                raise HTTPException(
                    422, "Ready valuation requires positive reviewed comparable amounts"
                )
            try:
                closed = date.fromisoformat(row["closed_on"])
                if (
                    closed.isoformat() != row["closed_on"]
                    or not 0 <= (datetime.now(UTC).date() - closed).days <= 730
                ):
                    raise ValueError("Invalid comparable close date")
            except (KeyError, TypeError, ValueError) as error:
                raise HTTPException(
                    422, "Ready valuation requires dated closed-sale evidence"
                ) from error
        count = valuation.get("comparable_count")
        ids = [row.get("sale_id") for row in snapshot["comparables"]]
        if (
            type(count) is not int
            or not 3 <= count <= 50
            or count != len(ids)
            or any(not isinstance(value, str) or not value for value in ids)
            or len(set(ids)) != count
        ):
            raise HTTPException(
                422, "Valuation requires matching distinct comparable evidence"
            )
        try:
            effective = date.fromisoformat(valuation["as_of"])
            age = (datetime.now(UTC).date() - effective).days
            if effective.isoformat() != valuation["as_of"] or not 0 <= age <= 30:
                raise ValueError("Stale valuation")
        except (KeyError, ValueError, TypeError) as error:
            raise HTTPException(422, "Current dated valuation required") from error
        amounts = [
            valuation.get(k)
            for k in ("supported_low_cents", "point_cents", "supported_high_cents")
        ]
        if any(
            type(v) is not int or not 0 < v <= 10**14 for v in amounts
        ) or amounts != sorted(amounts):
            raise HTTPException(422, "Invalid valuation amounts")
    for field in ("followups", "email_replies"):
        rows = snapshot.get(field, [])
        if not isinstance(rows, list) or len(rows) > 20:
            raise HTTPException(422, "Bounded operational records required")
        for row in rows:
            if (
                not isinstance(row, dict)
                or not isinstance(row.get("id"), str)
                or not 0 < len(row["id"]) <= 200
            ):
                raise HTTPException(422, "Operational identity required")
            stamp = row.get("at")
            if stamp is not None:
                try:
                    if (
                        datetime.fromisoformat(stamp.replace("Z", "+00:00")).tzinfo
                        is None
                    ):
                        raise ValueError("Timezone required")
                except (ValueError, TypeError, AttributeError) as error:
                    raise HTTPException(
                        422, "Dated operational records required"
                    ) from error
            if field == "email_replies" and (
                not isinstance(row.get("text"), str) or len(row["text"]) > 10000
            ):
                raise HTTPException(422, "Bounded reply text required")
    callback = snapshot.get("callback_at")
    if callback is not None:
        try:
            if datetime.fromisoformat(callback.replace("Z", "+00:00")).tzinfo is None:
                raise ValueError("Timezone required")
        except (ValueError, TypeError, AttributeError) as error:
            raise HTTPException(422, "Dated callback required") from error
    revision = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if body.get("revision") != revision:
        raise HTTPException(422, "Snapshot revision mismatch")
    try:
        observed = datetime.fromisoformat(body["occurred_at"].replace("Z", "+00:00"))
        if (
            observed.tzinfo is None
            or not -60 <= (datetime.now(UTC) - observed).total_seconds() <= 7 * 86400
        ):
            raise ValueError("Invalid observation time")
    except (KeyError, ValueError, TypeError, AttributeError) as error:
        raise HTTPException(422, "Dated snapshot required") from error
    return snapshot, revision, observed.astimezone(UTC).isoformat()


async def receive_business(session, body):
    snapshot, revision, observed = validate_snapshot(body)
    identity = str(body.get("call_sid") or "")
    if identity.startswith("lead:"):
        if identity != "lead:" + str(body.get("lead_id")):
            raise HTTPException(409, "Lead delivery partition mismatch")
    else:
        call = await find_call(session, identity)
        if body.get("lead_id") != (call.metadata_ or {}).get("external_lead_id"):
            raise HTTPException(409, "Call and lead binding mismatch")
    lead_id = await resolve_lead(session, body)
    if lead_id is None:
        raise HTTPException(422, "Bound lead required")
    lead = await session.get(Lead, lead_id)
    metadata = dict(lead.metadata_ or {})
    retained_after = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    receipts = {
        key: value
        for key, value in (metadata.get("business_receipts") or {}).items()
        if value.get("recorded_at", observed) >= retained_after
    }
    identity = str(body.get("call_sid") or "")
    if not 0 < len(identity) <= 255:
        raise HTTPException(422, "Delivery partition required")
    key = hashlib.sha256((identity + ":" + revision).encode()).hexdigest()
    if key in receipts:
        return {**receipts[key], "duplicate": True}
    if len(receipts) >= 5000:
        raise HTTPException(409, "Business snapshot receipt budget exhausted")
    current = metadata.get("business_evidence") or {}
    if current and current["snapshot"]["property_id"] != snapshot["property_id"]:
        raise HTTPException(409, "Canonical property binding changed; review required")
    if current.get("observed_at") == observed and current.get("revision") != revision:
        raise HTTPException(409, "Conflicting snapshots at the same observation time")
    if current.get("observed_at", "") > observed:
        status = "ignored_older_snapshot"
    else:
        status = "ok"
        metadata["business_evidence"] = {
            "snapshot": snapshot,
            "revision": revision,
            "observed_at": observed,
        }
        for field in ("address", "city", "state"):
            value = snapshot.get(field)
            if value is not None and (not isinstance(value, str) or len(value) > 500):
                raise HTTPException(422, "Invalid property label")
            setattr(lead, field, value)
    result = {
        "schema_version": 1,
        "persisted": True,
        "receipt_id": str(lead_id) + ":business:" + key,
        "call_sid": identity,
        "lead_id": str(lead_id),
        "status": status,
        "recorded_at": observed,
    }
    receipts[key] = result
    metadata["business_receipts"] = receipts
    lead.metadata_ = metadata
    await session.commit()
    return result


async def read_business(session, lead_id):
    lead = await session.scalar(
        select(Lead).where(Lead.id == lead_id, Lead.deleted_at.is_(None))
    )
    if lead is None:
        raise HTTPException(404, "Lead not found")

    return business_from_lead(lead)


def business_from_lead(lead):
    evidence = (lead.metadata_ or {}).get("business_evidence")
    if not evidence:
        return {"status": "unavailable", "snapshot": None}
    try:
        observed = datetime.fromisoformat(evidence["observed_at"])
        if observed.tzinfo is None:
            raise ValueError("Missing observation timezone")
        age = (datetime.now(UTC) - observed).total_seconds()
        valuation = evidence["snapshot"].get("valuation")
        valuation_age = (
            (datetime.now(UTC).date() - date.fromisoformat(valuation["as_of"])).days
            if valuation
            else 0
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        return {
            "status": "unavailable",
            "snapshot": None,
            "reason": "legacy_evidence_requires_review",
        }
    return {
        "status": "current"
        if 0 <= age <= 86400 and 0 <= valuation_age <= 30
        else "stale",
        **evidence,
    }
