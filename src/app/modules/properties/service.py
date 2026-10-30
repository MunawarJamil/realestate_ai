from __future__ import annotations

import logging
import math
import uuid
from decimal import Decimal

from app.modules.properties.enums import PropertyListingType, PropertyStatus, PropertyType
from app.modules.properties.exceptions import PropertyNotFoundError
from app.modules.properties.models import Property
from app.modules.properties.repository import PropertyRepository
from app.modules.properties.schemas import (
    CatalogQueryResponse,
    PropertyCreate,
    PropertyListResponse,
    PropertyRead,
    PropertySummary,
    PropertyUpdate,
)

logger = logging.getLogger(__name__)


def _to_summary(p: Property) -> PropertySummary:
    thumb = p.images[0] if p.images and len(p.images) > 0 else None
    return PropertySummary(
        id=p.id,
        title=p.title,
        property_type=p.property_type,
        listing_type=p.listing_type,
        price=p.price,
        currency=p.currency,
        location=p.location,
        bedrooms=p.bedrooms,
        bathrooms=p.bathrooms,
        area_sqft=p.area_sqft,
        thumbnail_url=thumb,
    )


class PropertyService:
    """Business operations and catalog queries for properties."""

    def __init__(self, repository: PropertyRepository) -> None:
        self._repository = repository

    async def create_property(
        self,
        *,
        tenant_id: uuid.UUID,
        data: PropertyCreate,
    ) -> PropertyRead:
        prop = await self._repository.create(
            tenant_id=tenant_id,
            property_data=data.model_dump(exclude_unset=True),
        )
        logger.info("Property created id=%s tenant_id=%s title=%s", prop.id, tenant_id, prop.title)
        return PropertyRead.model_validate(prop)

    async def get_property(
        self,
        *,
        tenant_id: uuid.UUID,
        property_id: uuid.UUID,
    ) -> PropertyRead:
        prop = await self._repository.get_by_id(tenant_id=tenant_id, property_id=property_id)
        if not prop:
            raise PropertyNotFoundError(f"Property {property_id} not found.")
        return PropertyRead.model_validate(prop)

    async def list_properties(
        self,
        *,
        tenant_id: uuid.UUID,
        status: PropertyStatus | None = None,
        property_type: PropertyType | None = None,
        listing_type: PropertyListingType | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        location: str | None = None,
        bedrooms: int | None = None,
        search: str | None = None,
        page: int = 1,
        size: int = 20,
        sort_by: str = "price",
        sort_desc: bool = False,
    ) -> PropertyListResponse:
        offset = (page - 1) * size
        props, total = await self._repository.query_catalog(
            tenant_id=tenant_id,
            status=status,
            property_type=property_type,
            listing_type=listing_type,
            min_price=min_price,
            max_price=max_price,
            location=location,
            bedrooms=bedrooms,
            search=search,
            offset=offset,
            limit=size,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )
        pages = math.ceil(total / size) if size > 0 else 0
        return PropertyListResponse(
            items=[PropertyRead.model_validate(p) for p in props],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    async def update_property(
        self,
        *,
        tenant_id: uuid.UUID,
        property_id: uuid.UUID,
        data: PropertyUpdate,
    ) -> PropertyRead:
        prop = await self._repository.get_by_id(tenant_id=tenant_id, property_id=property_id)
        if not prop:
            raise PropertyNotFoundError(f"Property {property_id} not found.")

        updated = await self._repository.update(
            prop=prop,
            update_data=data.model_dump(exclude_unset=True),
        )
        logger.info("Property updated id=%s tenant_id=%s", property_id, tenant_id)
        return PropertyRead.model_validate(updated)

    async def delete_property(
        self,
        *,
        tenant_id: uuid.UUID,
        property_id: uuid.UUID,
    ) -> None:
        deleted = await self._repository.delete(tenant_id=tenant_id, property_id=property_id)
        if not deleted:
            raise PropertyNotFoundError(f"Property {property_id} not found.")
        logger.info("Property deleted id=%s tenant_id=%s", property_id, tenant_id)

    async def query_inventory_for_agent(
        self,
        *,
        tenant_id: uuid.UUID,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        location: str | None = None,
        bedrooms: int | None = None,
        property_type: PropertyType | None = None,
        listing_type: PropertyListingType | None = None,
        limit: int = 5,
    ) -> CatalogQueryResponse:
        """Called by autonomous Agentic Tool (14.3.3) for exact filtering."""
        props, total = await self._repository.query_catalog(
            tenant_id=tenant_id,
            status=PropertyStatus.AVAILABLE,
            min_price=min_price,
            max_price=max_price,
            location=location,
            bedrooms=bedrooms,
            property_type=property_type,
            listing_type=listing_type,
            limit=limit,
        )

        summaries = [_to_summary(p) for p in props]

        if not summaries:
            criteria = []
            if property_type:
                criteria.append(str(property_type.value))
            if bedrooms:
                criteria.append(f"{bedrooms}-bedroom")
            if location:
                criteria.append(f"in {location}")
            if max_price:
                criteria.append(f"under {max_price:,.0f}")
            msg = f"No active listings found matching criteria: {', '.join(criteria) if criteria else 'specified filters'}."
        else:
            items_desc = [
                f"- **{s.title}** ({s.property_type.value}, {s.bedrooms or 'Studio'} beds, {s.location}): {s.currency} {s.price:,.2f}"
                for s in summaries
            ]
            msg = f"Found {total} properties matching criteria. Top options:\n" + "\n".join(items_desc)

        return CatalogQueryResponse(
            total_found=total,
            properties=summaries,
            summary_message=msg,
        )