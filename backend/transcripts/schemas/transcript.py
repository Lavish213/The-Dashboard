from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.enums import TranscriptSourceType, TranscriptStatus, TranscriptStreamType


class TranscriptCreate(BaseModel):
    workflow_id: UUID | None = None
    call_id: UUID | None = None
    lead_id: UUID | None = None
    source_type: TranscriptSourceType = TranscriptSourceType.call


class TranscriptChunkCreate(BaseModel):
    speaker: str
    text: str
    stream_type: TranscriptStreamType = TranscriptStreamType.user
    chunk_index: int | None = None


class TranscriptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID | None
    call_id: UUID | None
    lead_id: UUID | None
    transcript_status: TranscriptStatus
    source_type: TranscriptSourceType
    duration_seconds: int | None
    created_at: datetime
    updated_at: datetime


class TranscriptChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transcript_id: UUID
    chunk_index: int
    speaker: str
    text: str
    stream_type: TranscriptStreamType
    created_at: datetime


class TranscriptEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transcript_id: UUID
    event_type: str
    sequence: int
    payload: dict
    created_at: datetime
