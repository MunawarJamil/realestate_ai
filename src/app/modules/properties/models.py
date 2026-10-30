from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.properties.enums import PropertyListingType, PropertyStatus, PropertyType

if TYPE_CHECKING:
    from app.modules.tenants.models import Tenant


def _enum_values(enum_cls: Any) -> list[str]:
    return [m.value for m in enum_cls]


class Property(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "properties"
    __table_args__ = (
        Index("ix_props_tenant_status", "tenant_id", "status"),
        Index("ix_props_tenant_price", "tenant_id", "price"),
        Index("ix_props_tenant_type", "tenant_id", "property_type"),
        Index("ix_props_tenant_location", "tenant_id", "location"),
        Index("ix_props_tenant_beds", "tenant_id", "bedrooms"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    property_type: Mapped[PropertyType] = mapped_column(
        SAEnum(
            PropertyType,
            native_enum=False,
            length=30,
            values_callable=_enum_values,
        ),
        default=PropertyType.APARTMENT,
        server_default=text("'apartment'"),
        nullable=False,
        index=True,
    )

    listing_type: Mapped[PropertyListingType] = mapped_column(
        SAEnum(
            PropertyListingType,
            native_enum=False,
            length=20,
            values_callable=_enum_values,
        ),
        default=PropertyListingType.SALE,
        server_default=text("'sale'"),
        nullable=False,
    )

    status: Mapped[PropertyStatus] = mapped_column(
        SAEnum(
            PropertyStatus,
            native_enum=False,
            length=20,
            values_callable=_enum_values,
        ),
        default=PropertyStatus.AVAILABLE,
        server_default=text("'available'"),
        nullable=False,
        index=True,
    )

    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(10), default="AED", server_default=text("'AED'"), nullable=False)

    location: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    bathrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    area_sqft: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    amenities: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )
    images: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )

    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)

    tenant: Mapped[Tenant] = relationship("Tenant", foreign_keys=[tenant_id], lazy="selectin")