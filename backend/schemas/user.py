from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from models.enums import UserRole, UserStatus


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: UserRole = UserRole.operator


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    status: UserStatus | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    full_name: str | None
    role: UserRole
    status: UserStatus
    last_active_at: datetime | None
    created_at: datetime
    updated_at: datetime


class UserPublic(BaseModel):
    """Minimal user info safe to embed in other responses."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    full_name: str | None
    role: UserRole
