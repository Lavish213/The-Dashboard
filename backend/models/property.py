import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base
from models.base import TimestampMixin
from models.enums import PropertyStatus

if TYPE_CHECKING:
    from models.lead import Lead


class Property(Base, TimestampMixin):
    __tablename__ = "properties"

    __table_args__ = (
        sa.Index("ix_properties_city_state", "city", "state"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    address: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
    )
    city: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        index=True,
    )
    state: Mapped[str] = mapped_column(
        sa.String(2),
        nullable=False,
        index=True,
    )
    zip: Mapped[str | None] = mapped_column(
        sa.String(10),
        nullable=True,
    )
    latitude: Mapped[float | None] = mapped_column(
        sa.Float,
        nullable=True,
    )
    longitude: Mapped[float | None] = mapped_column(
        sa.Float,
        nullable=True,
    )
    estimated_value: Mapped[int | None] = mapped_column(
        sa.Integer,
        nullable=True,
    )
    property_status: Mapped[PropertyStatus] = mapped_column(
        sa.Enum(PropertyStatus, native_enum=True),
        nullable=False,
        default=PropertyStatus.active,
        index=True,
    )

    # Relationships
    leads: Mapped[list["Lead"]] = relationship(
        "Lead",
        back_populates="property",
    )
