import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func


class TimestampMixin:
    """Mixin that adds audit timestamp columns and a JSONB metadata column."""

    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata_",
        sa.JSON,
        nullable=False,
        default=dict,
    )
