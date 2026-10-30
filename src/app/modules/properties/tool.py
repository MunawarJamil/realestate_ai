"""
query_property_catalog: Agentic tool for querying structured inventory.

Invoked by the LangGraph tool router  Handles its own DB session
so it can run safely from any background orchestrator.
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from app.db.session import get_sessionmaker
from app.modules.properties.enums import PropertyListingType, PropertyType
from app.modules.properties.repository import PropertyRepository
from app.modules.properties.schemas import CatalogQueryResponse
from app.modules.properties.service import PropertyService

logger = logging.getLogger(__name__)

TOOL_NAME = "query_property_catalog"
TOOL_DESCRIPTION = (
    "Queries the agency's live property inventory database with structured filters. "
    "Use this tool when visitors ask for available properties with specific criteria, "
    "such as budget/price range (min_price, max_price), location, number of bedrooms, "
    "or property type (apartment, villa, townhouse, etc.)."
)


async def query_property_catalog(
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
    """Autonomous agentic tool — deterministic inventory filter query."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        service = PropertyService(repository=PropertyRepository(session))
        return await service.query_inventory_for_agent(
            tenant_id=tenant_id,
            min_price=min_price,
            max_price=max_price,
            location=location,
            bedrooms=bedrooms,
            property_type=property_type,
            listing_type=listing_type,
            limit=limit,
        )