import datetime
import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base
from models.base import TimestampMixin
from models.enums import WorkflowStatus, WorkflowType

if TYPE_CHECKING:
    from models.ai_decision import AIDecision
    from models.approval import Approval
    from models.call import Call
    from models.lead import Lead
    from models.transcript import Transcript
    from models.user import User
    from models.workflow_event import WorkflowEvent


class Workflow(Base, TimestampMixin):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    workflow_type: Mapped[WorkflowType] = mapped_column(
        sa.Enum(WorkflowType, native_enum=True),
        nullable=False,
        index=True,
    )
    workflow_status: Mapped[WorkflowStatus] = mapped_column(
        sa.Enum(WorkflowStatus, native_enum=True),
        nullable=False,
        default=WorkflowStatus.pending,
        index=True,
    )
    current_step: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=False,
        unique=True,
        default=uuid.uuid4,
        index=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("leads.id"),
        nullable=True,
        index=True,
    )
    initiated_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id"),
        nullable=True,
    )
    expires_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    lead: Mapped["Lead | None"] = relationship(
        "Lead",
        back_populates="workflows",
    )
    initiated_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[initiated_by],
    )
    workflow_events: Mapped[list["WorkflowEvent"]] = relationship(
        "WorkflowEvent",
        back_populates="workflow",
    )
    approvals: Mapped[list["Approval"]] = relationship(
        "Approval",
        back_populates="workflow",
    )
    ai_decisions: Mapped[list["AIDecision"]] = relationship(
        "AIDecision",
        back_populates="workflow",
    )
    transcripts: Mapped[list["Transcript"]] = relationship(
        "Transcript",
        back_populates="workflow",
    )
    calls: Mapped[list["Call"]] = relationship(
        "Call",
        back_populates="workflow",
    )
