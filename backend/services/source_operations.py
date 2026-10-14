from datetime import datetime

from services.business_evidence import business_from_lead


def source_operations(lead, view, start=None, end=None):
    evidence = business_from_lead(lead)
    snapshot = evidence.get("snapshot")
    if not isinstance(snapshot, dict):
        return []
    rows = []

    def add(identity, kind, state, at=None, amount=None, text=None):
        if not isinstance(identity, str) or not isinstance(state, str):
            return
        if at is not None:
            try:
                stamp = datetime.fromisoformat(at.replace("Z", "+00:00"))
                if (
                    stamp.tzinfo is None
                    or (start and stamp < start)
                    or (end and stamp >= end)
                ):
                    return
            except (ValueError, TypeError, AttributeError):
                return
        elif start or end:
            return
        rows.append(
            {
                "id": str(lead.id) + ":" + identity,
                "lead_id": str(lead.id),
                "full_name": lead.full_name,
                "kind": kind,
                "state": state,
                "at": at,
                "amount_cents": amount if type(amount) is int else None,
                "text": text,
                "source": "sophia",
                "evidence_status": evidence["status"],
                "observed_at": evidence.get("observed_at"),
                "revision": evidence.get("revision"),
                "property_id": snapshot.get("property_id"),
            }
        )

    if view == "deals":
        for row in snapshot.get("offers", [])[:20]:
            if isinstance(row, dict):
                add(
                    row.get("id"),
                    "offer",
                    row.get("status"),
                    row.get("updated_at"),
                    row.get("amount_cents"),
                )
    else:
        appointment = snapshot.get("appointment") or {}
        if (
            view == "calendar"
            and isinstance(appointment, dict)
            and appointment.get("status")
            in {"confirmed", "scheduled", "completed", "cancelled", "missed"}
            and appointment.get("at")
        ):
            add("appointment", "walkthrough", appointment["status"], appointment["at"])
        if snapshot.get("callback_at"):
            add("callback", "callback", "scheduled", snapshot["callback_at"])
        for row in snapshot.get("followups", [])[:20]:
            if isinstance(row, dict):
                add(
                    row.get("id"),
                    row.get("kind") or "followup",
                    row.get("state"),
                    row.get("at"),
                )
        if view == "followups":
            for row in snapshot.get("email_replies", [])[:20]:
                if isinstance(row, dict):
                    add(
                        row.get("id"),
                        "email_reply",
                        "needs_review",
                        row.get("at"),
                        text=row.get("text"),
                    )
    return rows
