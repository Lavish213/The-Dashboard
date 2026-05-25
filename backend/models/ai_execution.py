"""
AIExecution — persistent record of a single AI task execution.

Tracks full lifecycle: pending → running → completed/failed/cancelled.
Holds token budget, attempt counter, checkpoint state, and approval linkage.
Immutable audit columns: created_at, started_at, completed_at, cancelled_at.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base
from models.enums import AIExecutionStatus, AIProviderType, AITaskType


class AIExecution(Base):
    __tablename__ = "ai_executions"

    __table_args__ = (
        sa.Index("ix_ai_executions_workflow_id", "workflow_id"),
        sa.Index("ix_ai_executions_correlation_id", "correlation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Idempotency key — caller-supplied, unique per logical task invocation.
    # Same key submitted twice returns the existing execution, no duplicate created.
    execution_key: Mapped[str] = mapped_column(
        sa.String(512),
        nullable=False,
        unique=True,
    )
    task_type: Mapped[AITaskType] = mapped_column(
        sa.Enum(AITaskType, native_enum=True),
        nullable=False,
    )
    provider: Mapped[AIProviderType] = mapped_column(
        sa.Enum(AIProviderType, native_enum=True),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(
        sa.String(256),
        nullable=False,
    )
    status: Mapped[AIExecutionStatus] = mapped_column(
        sa.Enum(AIExecutionStatus, native_enum=True),
        nullable=False,
        default=AIExecutionStatus.pending,
        index=True,
    )
    # Optional workflow linkage
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
    )
    correlation_id: Mapped[str | None] = mapped_column(
        sa.String(256),
        nullable=True,
    )
    # Input/output blobs — immutable after write
    input_payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    output_payload: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    # Budgets and limits
    token_budget: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=4096,
    )
    tokens_used: Mapped[int | None] = mapped_column(
        sa.Integer,
        nullable=True,
    )
    timeout_seconds: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=30,
    )
    attempt: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
    )
    max_attempts: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=3,
    )
    # Lifecycle timestamps — append-only once set
    started_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    cancel_reason: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )
    # Resumable execution state — checkpoint blob
    checkpoint_state: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    # Approval gate linkage — set when execution pauses for approval
    requires_approval: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
    )
    # Advisory reference — no FK constraint; the gate owns approval lifecycle.
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    # Actor who triggered this execution
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        onupdate=func.clock_timestamp(),
        nullable=False,
    )
