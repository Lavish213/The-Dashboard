from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.social_post import SocialPost
from security.auth import get_current_active_user

router = APIRouter(dependencies=[Depends(get_current_active_user)])


def _serialize(p: SocialPost) -> dict:
    variants = None
    if p.spintax_variants:
        try:
            variants = json.loads(p.spintax_variants)
        except Exception:
            variants = [p.spintax_variants]
    return {
        "id": str(p.id),
        "platform": p.platform,
        "content": p.content,
        "spintax_variants": variants,
        "image_path": p.image_path,
        "target_group": p.target_group,
        "status": p.status,
        "post_type": p.post_type,
        "source_url": p.source_url,
        "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
        "posted_at": p.posted_at.isoformat() if p.posted_at else None,
        "comments_count": p.comments_count,
        "leads_generated": p.leads_generated,
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
    }


@router.get("")
async def list_posts(
    status: str | None = Query(None),
    platform: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    q = select(SocialPost)
    if status:
        q = q.where(SocialPost.status == status)
    if platform:
        q = q.where(SocialPost.platform == platform)
    q = q.order_by(SocialPost.created_at.desc())
    total_result = await session.execute(
        select(func.count()).select_from(q.subquery())
    )
    total = total_result.scalar_one()
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(q)
    posts = result.scalars().all()
    return {
        "items": [_serialize(p) for p in posts],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("")
async def create_post(
    body: dict,
    session: AsyncSession = Depends(get_session),
) -> dict:
    variants = body.get("spintax_variants")
    post = SocialPost(
        platform=body.get("platform", "facebook"),
        content=body.get("content", ""),
        spintax_variants=json.dumps(variants) if variants else None,
        image_path=body.get("image_path"),
        target_group=body.get("target_group"),
        status=body.get("status", "draft"),
        post_type=body.get("post_type"),
        source_url=body.get("source_url"),
        scheduled_at=datetime.fromisoformat(body["scheduled_at"]) if body.get("scheduled_at") else None,
    )
    session.add(post)
    await session.commit()
    return _serialize(post)


@router.patch("/{post_id}")
async def update_post(
    post_id: UUID,
    body: dict,
    session: AsyncSession = Depends(get_session),
) -> dict:
    from fastapi import HTTPException
    result = await session.execute(select(SocialPost).where(SocialPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    for field in ["content", "status", "platform", "target_group", "post_type", "image_path", "source_url"]:
        if field in body:
            setattr(post, field, body[field])
    if "spintax_variants" in body:
        post.spintax_variants = json.dumps(body["spintax_variants"]) if body["spintax_variants"] else None
    if "scheduled_at" in body:
        post.scheduled_at = datetime.fromisoformat(body["scheduled_at"]) if body["scheduled_at"] else None
    if body.get("status") == "posted":
        post.posted_at = datetime.now(UTC)
    session.add(post)
    await session.commit()
    return _serialize(post)


@router.delete("/{post_id}")
async def delete_post(
    post_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    from fastapi import HTTPException
    result = await session.execute(select(SocialPost).where(SocialPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    await session.delete(post)
    await session.commit()
    return {"status": "ok"}


@router.get("/analytics")
async def social_analytics(
    session: AsyncSession = Depends(get_session),
) -> dict:
    total_result = await session.execute(select(func.count()).select_from(SocialPost))
    total = total_result.scalar_one()

    posted_result = await session.execute(
        select(func.count()).select_from(SocialPost).where(SocialPost.status == "posted")
    )
    posted = posted_result.scalar_one()

    leads_result = await session.execute(
        select(func.sum(SocialPost.leads_generated)).select_from(SocialPost)
    )
    total_leads = leads_result.scalar_one() or 0

    platform_result = await session.execute(
        select(SocialPost.platform, func.count())
        .group_by(SocialPost.platform)
    )
    by_platform = {row[0]: row[1] for row in platform_result.all()}

    return {
        "total_posts": total,
        "posted": posted,
        "total_leads_generated": total_leads,
        "by_platform": by_platform,
    }