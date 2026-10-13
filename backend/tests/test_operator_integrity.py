from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, WebSocketException

from api.routes import leads, notifications, settings
from db.session import get_session
from models.enums import LeadStatus, NotificationType, UserRole, UserStatus
from models.lead import Lead
from models.notification import Notification
from models.user import User
from security.auth import (
    create_access_token,
    get_current_active_user,
    get_current_user_ws,
)


def application(router, db, user):
    app = FastAPI()
    app.include_router(router, prefix="/test")

    async def database():
        yield db

    app.dependency_overrides[get_session] = database
    app.dependency_overrides[get_current_active_user] = lambda: user
    return app


async def user_for(db, role=UserRole.operator):
    user = User(email=f"{uuid4()}@example.invalid", full_name="Synthetic operator", role=role, status=UserStatus.active)
    db.add(user)
    await db.flush()
    return user


async def test_scheduling_filters_before_paginating_over_200(db):
    user = await user_for(db)
    start = datetime(2099, 2, 1, tzinfo=UTC)
    db.add_all([Lead(full_name=f"Unscheduled {i}") for i in range(210)])
    db.add_all([Lead(full_name=f"Scheduled {i}", follow_up_at=start + timedelta(days=1, minutes=i)) for i in range(205)])
    db.add(Lead(full_name="Other month", follow_up_at=start + timedelta(days=40)))
    db.add(Lead(full_name="Deleted", follow_up_at=start + timedelta(days=1), deleted_at=datetime.now(UTC)))
    await db.flush()
    params = {"scheduled_only": "true", "follow_up_start": start.isoformat(), "follow_up_end": (start + timedelta(days=28)).isoformat(), "page_size": 200}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(leads.router, db, user)), base_url="http://test") as client:
        first = await client.get("/test", params=params)
        second = await client.get("/test", params={**params, "page": 2})
        bad = await client.get("/test", params={**params, "follow_up_start": "2099-02-01T00:00:00"})
    assert first.status_code == second.status_code == 200
    assert first.json()["total"] == 205 and first.json()["total_pages"] == 2
    assert len(first.json()["items"]) == 200 and len(second.json()["items"]) == 5
    assert not ({r["id"] for r in first.json()["items"]} & {r["id"] for r in second.json()["items"]})
    assert bad.status_code == 422


async def test_deal_totals_cover_all_pages_and_multiple_statuses(db):
    user = await user_for(db)
    db.add_all([Lead(full_name=f"Deal {i}", lead_status=LeadStatus.qualified, ai_score=80) for i in range(205)])
    db.add(Lead(full_name="Converted", lead_status=LeadStatus.converted, ai_score=90))
    db.add(Lead(full_name="Not a deal", ai_score=99))
    await db.flush()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(leads.router, db, user)), base_url="http://test") as client:
        response = await client.get("/test", params=[("statuses", "qualified"), ("statuses", "converted"), ("page_size", "200")])
    data = response.json()
    assert data["total"] == 206 and len(data["items"]) == 200
    assert data["summary"]["by_status"] == {"qualified": 205, "converted": 1}
    assert data["summary"]["score_total"] == 205 * 80 + 90


async def test_followup_save_then_cancel_is_acknowledged(db):
    user = await user_for(db)
    lead = Lead(full_name="Synthetic seller")
    db.add(lead)
    await db.flush()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(leads.router, db, user)), base_url="http://test") as client:
        saved = await client.patch(f"/test/{lead.id}/followup", json={"follow_up_at": "2099-04-02T10:00:00-07:00"})
        cancelled = await client.patch(f"/test/{lead.id}/followup", json={"follow_up_at": None})
    assert saved.status_code == cancelled.status_code == 200
    assert saved.json()["follow_up_at"].startswith("2099-04-02T17:00:00")
    assert cancelled.json()["follow_up_at"] is None
    await db.refresh(lead)
    assert lead.follow_up_at is None


async def test_own_notification_feed_and_read_cannot_touch_other_user(db, monkeypatch):
    owner, other = await user_for(db), await user_for(db)
    mine = Notification(user_id=owner.id, notification_type=NotificationType.system_alert, title="Own", body="Own body")
    theirs = Notification(user_id=other.id, notification_type=NotificationType.system_alert, title="Other", body="Other body")
    db.add_all([mine, theirs])
    await db.flush()
    monkeypatch.setattr("services.notifications.broadcast_service.publish", AsyncMock(return_value=0))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(notifications.router, db, owner)), base_url="http://test") as client:
        feed = await client.get("/test")
        forbidden = await client.post(f"/test/{theirs.id}/read")
        read = await client.post(f"/test/{mine.id}/read")
        count = await client.get("/test/unread-count")
    assert [n["title"] for n in feed.json()["items"]] == ["Own"]
    assert forbidden.status_code == 404 and read.status_code == 200
    assert count.json()["unread_count"] == 0
    await db.refresh(theirs)
    assert theirs.read_at is None


async def test_commit_failure_cannot_publish_notification_success(db, monkeypatch):
    owner = await user_for(db)
    mine = Notification(user_id=owner.id, notification_type=NotificationType.system_alert, title="Own", body="Own body")
    db.add(mine)
    await db.flush()
    publish = AsyncMock(return_value=0)
    monkeypatch.setattr("services.notifications.broadcast_service.publish", publish)
    monkeypatch.setattr(db, "commit", AsyncMock(side_effect=RuntimeError("Synthetic commit failure")))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(notifications.router, db, owner), raise_app_exceptions=False), base_url="http://test") as client:
        response = await client.post(f"/test/{mine.id}/read")
    assert response.status_code == 500
    publish.assert_not_awaited()


async def test_team_roster_is_paginated_and_excludes_deleted_users(db):
    admin = await user_for(db, UserRole.admin)
    hidden = User(email=f"{uuid4()}@example.invalid", role=UserRole.operator, deleted_at=datetime.now(UTC))
    db.add(hidden)
    await db.flush()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(settings.router, db, admin)), base_url="http://test") as client:
        response = await client.get("/test/team", params={"page_size": 1})
    data = response.json()
    assert data["total"] == 1 and data["items"][0]["id"] == str(admin.id)
    assert "hashed_password" not in data["items"][0]


async def test_realtime_identity_uses_current_database_role(db):
    user = await user_for(db, UserRole.reviewer)
    token = create_access_token(str(user.id), {"role": "admin"})
    redis = AsyncMock(exists=AsyncMock(return_value=0))
    identity = await get_current_user_ws(token, db, redis)
    assert identity.role == UserRole.reviewer


@pytest.mark.parametrize("state", ["inactive", "deleted", "missing"])
async def test_realtime_identity_rejects_revoked_or_missing_accounts(db, state):
    user = await user_for(db)
    if state == "inactive":
        user.status = UserStatus.inactive
    if state == "deleted":
        user.deleted_at = datetime.now(UTC)
    await db.flush()
    token = create_access_token(str(uuid4() if state == "missing" else user.id))
    with pytest.raises(WebSocketException):
        await get_current_user_ws(token, db, AsyncMock(exists=AsyncMock(return_value=0)))
