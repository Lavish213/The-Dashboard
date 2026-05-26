from __future__ import annotations

import uuid
import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from models.base import TimestampMixin


class SocialPost(Base, TimestampMixin):
    __tablename__ = "social_posts"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    platform: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    spintax_variants: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )
    image_path: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    target_group: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        default="draft",
        index=True,
    )
    scheduled_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    posted_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    source_url: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    post_type: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    comments_count: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
    )
    leads_generated: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
    )