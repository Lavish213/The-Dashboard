from fastapi import Depends, HTTPException, Request

from models.enums import UserRole
from security.auth import get_current_active_user


async def require_legacy_writer(
    request: Request, user=Depends(get_current_active_user)
):
    if request.method not in {"GET", "HEAD", "OPTIONS"} and user.role not in {
        UserRole.admin,
        UserRole.operator,
    }:
        raise HTTPException(403, "Write permission required")
    return user
