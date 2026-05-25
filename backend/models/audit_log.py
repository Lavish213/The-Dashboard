import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.base import Base
from models.enums import AuditActorType


class AuditLog(Base):
    __tablename__ = "audit_logs"

    __table_args__ = (
        sa.Index("ix_audit_logs_actor_id_created_at", "actor_id", "created_at"),
        sa.Index("ix_audit_logs_target_type_target_id", "target_type", "target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    actor_type: Mapped[AuditActorType] = mapped_column(
        sa.Enum(AuditActorType, native_enum=True),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        index=True,
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    ip_address: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    payload: Mapped[dict] = mapped_column(
        sa.JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )
