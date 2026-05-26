from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from models.base import TimestampMixin


class Referral(Base, TimestampMixin):
    __tablename__ = "referrals"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    referrer_name: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
    )
    referrer_type: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    referrer_phone: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    referrer_email: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    fee_amount: Mapped[int | None] = mapped_column(
        sa.Integer,
        nullable=True,
    )
    fee_status: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        default="pending",
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )
