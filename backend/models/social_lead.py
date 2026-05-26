from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from models.base import TimestampMixin


class SocialLead(Base, TimestampMixin):
    __tablename__ = "social_leads"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    full_name: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    phone: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    platform: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        index=True,
    )
    source_post_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    message: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )
    intent_score: Mapped[int | None] = mapped_column(
        sa.Integer,
        nullable=True,
    )
    intent_label: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        default="new",
        index=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    profile_url: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )