import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from db.session import Base
from models.enums import AuditActorType

if TYPE_CHECKING:
    from models.workflow import Workflow


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"

    __table_args__ = (
        sa.Index("ix_workflow_events_workflow_id_created_at", "workflow_id", "created_at"),
        sa.Index("ix_workflow_events_correlation_id", "correlation_id"),
        sa.Index("ix_workflow_events_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("workflows.id"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        index=True,
    )
    payload: Mapped[dict] = mapped_column(
        sa.JSON,
        nullable=False,
        default=dict,
    )
    causation_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    actor_type: Mapped[AuditActorType] = mapped_column(
        sa.Enum(AuditActorType, native_enum=True),
        nullable=False,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata_",
        sa.JSON,
        nullable=False,
        default=dict,
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        back_populates="workflow_events",
    )
