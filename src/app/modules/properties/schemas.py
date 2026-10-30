from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.properties.enums import PropertyListingType, PropertyStatus, PropertyType


class PropertyBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    property_type: PropertyType = PropertyType.APARTMENT
    listing_type: PropertyListingType = PropertyListingType.SALE
    price: Decimal = Field(...,  gt=Decimal("0"))
    currency: str = Field(default="AED", max_length=10)
    location: str = Field(..., min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    area_sqft: Decimal | None = Field(default=None,  gt=Decimal("0"))
    amenities: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    is_featured: bool = False


class PropertyCreate(PropertyBase):
    status: PropertyStatus = PropertyStatus.AVAILABLE


class PropertyUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    property_type: PropertyType | None = None
    listing_type: PropertyListingType | None = None
    status: PropertyStatus | None = None
    price: Decimal | None = Field(default=None,  gt=Decimal("0"))
    currency: str | None = Field(default=None, max_length=10)
    location: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    area_sqft: Decimal | None = Field(default=None,  gt=Decimal("0"))
    amenities: list[str] | None = None
    images: list[str] | None = None
    is_featured: bool | None = None


class PropertyRead(PropertyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    status: PropertyStatus
    created_at: datetime
    updated_at: datetime


class PropertySummary(BaseModel):
    """Compact property summary payload for LLM tools and lists."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    property_type: PropertyType
    listing_type: PropertyListingType
    price: Decimal
    currency: str
    location: str
    bedrooms: int | None
    bathrooms: int | None
    area_sqft: Decimal | None
    thumbnail_url: str | None = None


class PropertyListResponse(BaseModel):
    items: list[PropertyRead]
    total: int
    page: int
    size: int
    pages: int


class CatalogQueryResponse(BaseModel):
    """Result returned by structured inventory query tool to LLM."""
    total_found: int
    properties: list[PropertySummary]
    summary_message: str