from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from db.session import get_session
from models.user import User
from security.auth import get_current_active_user
from security.permissions import require_permission
from security.rbac import ROLE_PERMISSIONS, Permission

router = APIRouter(dependencies=[Depends(get_current_active_user)])


@router.get("")
async def configuration(user: User = Depends(get_current_active_user)) -> dict:
    return {
        "source": "dashboard_server",
        "app_version": settings.app_version,
        "environment": settings.app_env,
        "security": {
            "access_token_minutes": settings.access_token_expire_minutes,
            "refresh_token_days": settings.refresh_token_expire_days,
        },
        "permissions": sorted(p.value for p in ROLE_PERMISSIONS.get(user.role, frozenset())),
        "notifications": {"channel": "in_app", "delivery": "database_and_websocket"},
        "voice_configuration": {"available": False, "reason": "Voice provider configuration is managed by the separate voice service"},
        "calendar_booking": {"available": False, "reason": "This dashboard exposes lead follow-up dates, not external availability or bookings"},
    }


@router.get("/team", dependencies=[Depends(require_permission(Permission.USERS_READ))])
async def team(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> dict:
    total = await session.scalar(select(func.count()).select_from(User).where(User.deleted_at.is_(None)))
    users = (await session.scalars(select(User).where(User.deleted_at.is_(None)).order_by(User.email, User.id).offset((page - 1) * page_size).limit(page_size))).all()
    return {
        "items": [{"id": str(u.id), "full_name": u.full_name, "email": u.email, "role": u.role.value, "status": u.status.value} for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }
