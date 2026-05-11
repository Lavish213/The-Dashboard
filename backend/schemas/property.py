from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.enums import PropertyStatus


class PropertyCreate(BaseModel):
    address: str
    city: str
    state: str
    zip: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    estimated_value: int | None = None  # cents


class PropertyUpdate(BaseModel):
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    estimated_value: int | None = None
    property_status: PropertyStatus | None = None


class PropertyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    address: str
    city: str
    state: str
    zip: str | None
    latitude: float | None
    longitude: float | None
    estimated_value: int | None
    property_status: PropertyStatus
    created_at: datetime
    updated_at: datetime
