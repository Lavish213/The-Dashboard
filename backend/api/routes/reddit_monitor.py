from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from security.auth import get_current_active_user

router = APIRouter(dependencies=[Depends(get_current_active_user)])


def _serialize(r) -> dict:
    return {
        "id": str(r.id),
        "reddit_id": r.reddit_id,
        "subreddit": r.subreddit,
        "title": r.title,
        "body": r.body,
        "url": r.url,
        "author": r.author,
        "created_utc": r.created_utc,
        "post_score": r.post_score,
        "intent_score": r.intent_score,
        "intent_label": r.intent_label,
        "status": r.status,
        "lead_id": str(r.lead_id) if r.lead_id else None,
        "created_at": r.created_at.isoformat(),
    }


@router.get("")
async def list_reddit_matches(
    intent_label: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    from models.reddit_match import RedditMatch

    q = select(RedditMatch)
    if intent_label:
        q = q.where(RedditMatch.intent_label == intent_label)
    if status:
        q = q.where(RedditMatch.status == status)
    q = q.order_by(desc(RedditMatch.intent_score), desc(RedditMatch.created_at))

    total_result = await session.execute(
        select(func.count()).select_from(q.subquery())
    )
    total = total_result.scalar_one()
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(q)
    matches = result.scalars().all()

    return {
        "items": [_serialize(m) for m in matches],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.patch("/{match_id}/status")
async def update_match_status(
    match_id: UUID,
    body: dict,
    session: AsyncSession = Depends(get_session),
) -> dict:
    from fastapi import HTTPException
    from models.reddit_match import RedditMatch

    result = await session.execute(
        select(RedditMatch).where(RedditMatch.id == match_id)
    )
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.status = body.get("status", match.status)
    if body.get("lead_id"):
        match.lead_id = body["lead_id"]
    session.add(match)
    await session.commit()
    return {"status": "ok"}


@router.post("/scan")
async def trigger_scan(
    session: AsyncSession = Depends(get_session),
) -> dict:
    from workers.reddit_monitor import run_once
    count = await run_once(session)
    return {"status": "ok", "new_matches": count}