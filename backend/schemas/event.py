from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.enums import AuditActorType


class WorkflowEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    workflow_id: UUID
    event_type: str
    payload: dict
    causation_id: UUID | None
    correlation_id: UUID
    actor_type: AuditActorType
    actor_id: UUID | None
    created_at: datetime


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    actor_id: UUID | None
    actor_type: AuditActorType
    action: str
    target_type: str
    target_id: UUID | None
    correlation_id: UUID | None
    ip_address: str | None
    payload: dict
    created_at: datetime
