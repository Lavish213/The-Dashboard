from fastapi import Depends, HTTPException

from models.user import User
from security.auth import get_current_active_user
from security.rbac import Permission, has_permission


def require_permission(permission: Permission):
    """Returns a FastAPI dependency that enforces a permission."""
    async def dependency(user: User = Depends(get_current_active_user)) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return dependency


def require_role(*roles: str):
    """Returns a FastAPI dependency that enforces user role membership."""
    async def dependency(user: User = Depends(get_current_active_user)) -> User:
        if user.role.value not in roles:
            raise HTTPException(status_code=403, detail="Role not authorized")
        return user
    return dependency


require_admin = require_role("admin")
