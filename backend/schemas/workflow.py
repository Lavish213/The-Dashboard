from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.enums import WorkflowStatus, WorkflowType


class WorkflowCreate(BaseModel):
    workflow_type: WorkflowType
    lead_id: UUID | None = None
    initiated_by: UUID | None = None
    expires_at: datetime | None = None


class WorkflowUpdate(BaseModel):
    workflow_status: WorkflowStatus | None = None
    current_step: str | None = None
    expires_at: datetime | None = None


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    workflow_type: WorkflowType
    workflow_status: WorkflowStatus
    current_step: str | None
    correlation_id: UUID
    lead_id: UUID | None
    initiated_by: UUID | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
