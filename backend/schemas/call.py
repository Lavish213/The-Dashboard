from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.enums import CallProvider, CallStatus


class CallCreate(BaseModel):
    lead_id: UUID | None = None
    workflow_id: UUID | None = None
    provider: CallProvider = CallProvider.twilio
    provider_call_id: str | None = None


class CallUpdate(BaseModel):
    call_status: CallStatus | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    recording_url: str | None = None


class CallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    lead_id: UUID | None
    workflow_id: UUID | None
    provider: CallProvider
    call_status: CallStatus
    provider_call_id: str | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    recording_url: str | None
    created_at: datetime
    updated_at: datetime
