from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.enums import ApprovalStatus, ApprovalType, RiskLevel


class ApprovalCreate(BaseModel):
    workflow_id: UUID
    approval_type: ApprovalType
    requested_by: UUID | None = None
    expires_at: datetime | None = None
    risk_level: RiskLevel = RiskLevel.low


class ApprovalResolve(BaseModel):
    approval_status: ApprovalStatus  # approved or rejected
    resolved_by: UUID
    resolution_notes: str | None = None


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    workflow_id: UUID
    approval_type: ApprovalType
    approval_status: ApprovalStatus
    requested_by: UUID | None
    resolved_by: UUID | None
    expires_at: datetime | None
    risk_level: RiskLevel
    resolution_notes: str | None
    created_at: datetime
    updated_at: datetime
