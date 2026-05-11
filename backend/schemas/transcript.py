from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.enums import TranscriptStatus


class TranscriptCreate(BaseModel):
    lead_id: UUID | None = None
    workflow_id: UUID | None = None
    call_id: UUID | None = None


class TranscriptUpdate(BaseModel):
    transcript_status: TranscriptStatus | None = None
    summary: str | None = None
    duration_seconds: int | None = None


class TranscriptSegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    transcript_id: UUID
    speaker: str
    text: str
    start_ms: int
    end_ms: int
    sentiment: str | None
    emotion: str | None
    sequence_number: int


class TranscriptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    lead_id: UUID | None
    workflow_id: UUID | None
    call_id: UUID | None
    transcript_status: TranscriptStatus
    summary: str | None
    duration_seconds: int | None
    created_at: datetime
    updated_at: datetime
