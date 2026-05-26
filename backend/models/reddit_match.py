from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from models.base import TimestampMixin


class RedditMatch(Base, TimestampMixin):
    __tablename__ = "reddit_matches"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    reddit_id: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        unique=True,
        index=True,
    )
    subreddit: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    body: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )
    url: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
    )
    author: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    created_utc: Mapped[int | None] = mapped_column(
        sa.Integer,
        nullable=True,
    )
    post_score: Mapped[int | None] = mapped_column(
        sa.Integer,
        nullable=True,
    )
    intent_score: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
        index=True,
    )
    intent_label: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        default="none",
        index=True,
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