import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base
from models.base import TimestampMixin
from models.enums import DecisionType

if TYPE_CHECKING:
    from models.transcript import Transcript
    from models.workflow import Workflow


class AIDecision(Base, TimestampMixin):
    __tablename__ = "ai_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("workflows.id"),
        nullable=True,
        index=True,
    )
    transcript_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("transcripts.id"),
        nullable=True,
        index=True,
    )
    decision_type: Mapped[DecisionType] = mapped_column(
        sa.Enum(DecisionType, native_enum=True),
        nullable=False,
        index=True,
    )
    confidence: Mapped[float | None] = mapped_column(
        sa.Float,
        nullable=True,
    )
    reasoning: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )
    model_name: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    input_summary: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )
    output_summary: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )

    # Relationships
    workflow: Mapped["Workflow | None"] = relationship(
        "Workflow",
        back_populates="ai_decisions",
    )
    transcript: Mapped["Transcript | None"] = relationship(
        "Transcript",
    )
