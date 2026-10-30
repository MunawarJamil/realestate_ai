from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.properties.enums import PropertyListingType, PropertyStatus, PropertyType
from app.modules.properties.models import Property
from sqlalchemy.engine import CursorResult
from typing import cast

class PropertyRepository:
    """Async database operations for property inventory with strict tenant-isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        tenant_id: uuid.UUID,
        property_data: dict[str, Any],
    ) -> Property:
        prop = Property(tenant_id=tenant_id, **property_data)
        self._session.add(prop)
        await self._session.flush()
        await self._session.refresh(prop)
        return prop

    async def get_by_id(
        self,
        *,
        tenant_id: uuid.UUID,
        property_id: uuid.UUID,
    ) -> Property | None:
        stmt = select(Property).where(
            Property.id == property_id,
            Property.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def query_catalog(
        self,
        *,
        tenant_id: uuid.UUID,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        location: str | None = None,
        bedrooms: int | None = None,
        property_type: PropertyType | None = None,
        listing_type: PropertyListingType | None = None,
        status: PropertyStatus | None = PropertyStatus.AVAILABLE,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
        sort_by: str = "price",
        sort_desc: bool = False,
    ) -> tuple[Sequence[Property], int]:
        filters = [Property.tenant_id == tenant_id]

        if status is not None:
            filters.append(Property.status == status)
        if min_price is not None:
            filters.append(Property.price >= min_price)
        if max_price is not None:
            filters.append(Property.price <= max_price)
        if bedrooms is not None:
            filters.append(Property.bedrooms == bedrooms)
        if property_type is not None:
            filters.append(Property.property_type == property_type)
        if listing_type is not None:
            filters.append(Property.listing_type == listing_type)
        if location and location.strip():
            filters.append(Property.location.ilike(f"%{location.strip()}%"))

        if search and search.strip():
            term = f"%{search.strip()}%"
            filters.append(
                or_(
                    Property.title.ilike(term),
                    Property.location.ilike(term),
                    Property.address.ilike(term),
                    Property.description.ilike(term),
                )
            )

        where_clause = and_(*filters)
        count_stmt = select(func.count(Property.id)).where(where_clause)

        sort_col = getattr(Property, sort_by, Property.price)
        query_stmt = (
            select(Property)
            .where(where_clause)
            .order_by(desc(sort_col) if sort_desc else sort_col)
            .offset(offset)
            .limit(limit)
        )

        total = (await self._session.execute(count_stmt)).scalar() or 0
        items = (await self._session.execute(query_stmt)).scalars().all()
        return items, total

    async def update(
        self,
        *,
        prop: Property,
        update_data: dict[str, Any],
    ) -> Property:
        for key, value in update_data.items():
            setattr(prop, key, value)
        await self._session.flush()
        await self._session.refresh(prop)
        return prop

    async def delete(
        self,
        *,
        tenant_id: uuid.UUID,
        property_id: uuid.UUID,
    ) -> bool:
        stmt = delete(Property).where(
            Property.id == property_id,
            Property.tenant_id == tenant_id,
        )
        res = await self._session.execute(stmt)
        await self._session.flush()
 
        return cast(CursorResult, res).rowcount > 0