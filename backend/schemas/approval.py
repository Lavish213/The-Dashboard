from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.enums import ApprovalStatus, ApprovalType, RiskLevel


class ApprovalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workflow_id: UUID
    approval_type: ApprovalType
    requested_by: UUID | None = None
    expires_at: datetime | None = None
    risk_level: RiskLevel = RiskLevel.low

    @field_validator("expires_at")
    @classmethod
    def future_expiry(cls, value):
        if value is not None and (value.tzinfo is None or value <= datetime.now(UTC)):
            raise ValueError("Approval expiry must be a future timezone-aware timestamp")
        return value


class ApprovalResolve(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approval_status: ApprovalStatus  # approved or rejected
    resolved_by: UUID | None = None
    resolution_notes: str | None = Field(default=None, max_length=5000)


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
