"""Call runtime schemas — typed request/response only. No AI fields."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.enums import CallSessionStatus, ParticipantRole, ParticipantStatus


class CallSessionCreate(BaseModel):
    call_id: UUID | None = None


class CallSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    call_id: UUID | None
    session_status: CallSessionStatus
    correlation_id: UUID
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CallParticipantJoin(BaseModel):
    user_id: UUID | None = None
    role: ParticipantRole
    connection_id: str | None = None


class CallParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    session_id: UUID
    user_id: UUID | None
    role: ParticipantRole
    participant_status: ParticipantStatus
    connection_id: str | None
    joined_at: datetime
    left_at: datetime | None
    last_heartbeat_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CallEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    session_id: UUID
    event_type: str
    sequence: int
    payload: dict
    created_at: datetime


class PresenceUpdate(BaseModel):
    participant_id: UUID
    connection_id: str


class ConnectionStateResponse(BaseModel):
    participant_id: UUID
    session_id: UUID
    participant_status: ParticipantStatus
    connection_id: str | None
    last_heartbeat_at: datetime | None
    is_stale: bool
