from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.enums import LeadSource, LeadStatus


class LeadCreate(BaseModel):
    full_name: str
    phone: str | None = None
    email: str | None = None
    lead_source: LeadSource | None = None
    assigned_user_id: UUID | None = None
    property_id: UUID | None = None


class LeadUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    lead_status: LeadStatus | None = None
    lead_source: LeadSource | None = None
    assigned_user_id: UUID | None = None
    property_id: UUID | None = None
    ai_score: int | None = None


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    full_name: str
    phone: str | None
    email: str | None
    lead_status: LeadStatus
    lead_source: LeadSource | None
    assigned_user_id: UUID | None
    property_id: UUID | None
    ai_score: int | None
    last_contacted_at: datetime | None
    created_at: datetime
    updated_at: datetime
