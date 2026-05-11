import datetime
import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base
from models.base import TimestampMixin
from models.enums import ApprovalStatus, ApprovalType, RiskLevel

if TYPE_CHECKING:
    from models.user import User
    from models.workflow import Workflow


class Approval(Base, TimestampMixin):
    __tablename__ = "approvals"

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
    approval_type: Mapped[ApprovalType] = mapped_column(
        sa.Enum(ApprovalType, native_enum=True),
        nullable=False,
    )
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        sa.Enum(ApprovalStatus, native_enum=True),
        nullable=False,
        default=ApprovalStatus.pending,
        index=True,
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id"),
        nullable=True,
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id"),
        nullable=True,
    )
    expires_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        sa.Enum(RiskLevel, native_enum=True),
        nullable=False,
        default=RiskLevel.low,
    )
    resolution_notes: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        back_populates="approvals",
    )
    requested_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[requested_by],
    )
    resolved_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[resolved_by],
    )
