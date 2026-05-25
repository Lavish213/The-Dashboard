import datetime
import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from models.base import TimestampMixin
from models.enums import LeadSource, LeadStatus

if TYPE_CHECKING:
    from models.call import Call
    from models.property import Property
    from models.transcript import Transcript
    from models.user import User
    from models.workflow import Workflow


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    full_name: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
    )
    phone: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
        index=True,
    )
    email: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    lead_status: Mapped[LeadStatus] = mapped_column(
        sa.Enum(LeadStatus, native_enum=True),
        nullable=False,
        default=LeadStatus.new,
        index=True,
    )
    lead_source: Mapped[LeadSource | None] = mapped_column(
        sa.Enum(LeadSource, native_enum=True),
        nullable=True,
    )
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("properties.id"),
        nullable=True,
        index=True,
    )
    ai_score: Mapped[int | None] = mapped_column(
        sa.Integer,
        nullable=True,
    )
    last_contacted_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    assigned_user: Mapped["User | None"] = relationship(
        "User",
        back_populates="leads",
        foreign_keys=[assigned_user_id],
    )
    property: Mapped["Property | None"] = relationship(
        "Property",
        back_populates="leads",
    )
    workflows: Mapped[list["Workflow"]] = relationship(
        "Workflow",
        back_populates="lead",
    )
    calls: Mapped[list["Call"]] = relationship(
        "Call",
        back_populates="lead",
    )
    transcripts: Mapped[list["Transcript"]] = relationship(
        "Transcript",
        back_populates="lead",
    )
