"""
DomainEvent — canonical event schema for the Karpathys realtime event log.

DomainEvent: input schema (create/emit).
StoredEvent: output schema (after persistence, includes seq_num).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    channel: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StoredEvent(DomainEvent):
    seq_num: int
