from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

from app.modules.bookings.tool import (
    TOOL_DESCRIPTION as BOOKING_DESC,
    TOOL_NAME as BOOKING_NAME,
    schedule_viewing,
)
   
from app.modules.calculator.tool import (
    TOOL_DESCRIPTION as CALC_DESC,
    TOOL_NAME as CALC_NAME,
    calculate_mortgage_tool,
)
from app.modules.properties.enums import PropertyListingType, PropertyType
from app.modules.properties.tool import (
    TOOL_DESCRIPTION as CATALOG_DESC,
    TOOL_NAME as CATALOG_NAME,
    query_property_catalog,
)

logger = logging.getLogger(__name__)


# ── OpenAI / LangChain compatible JSON schemas for Function Calling ──────────

TOOLS_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": BOOKING_NAME,
            "description": BOOKING_DESC,
            "parameters": {
                "type": "object",
                "properties": {
                    "visitor_name": {
                        "type": "string",
                        "description": "Full name of the visitor requesting the viewing",
                    },
                    "phone": {
                        "type": "string",
                        "description": "Visitor contact phone number",
                    },
                    "preferred_time": {
                        "type": "string",
                        "description": "ISO-8601 formatted datetime for the viewing (e.g., '2026-11-05T14:00:00Z')",
                    },
                    "property_ref": {
                        "type": "string",
                        "description": "Property title, address, or ID the visitor wants to view",
                    },
                    "email": {
                        "type": "string",
                        "description": "Optional email address of the visitor",
                    },
                },
                "required": ["visitor_name", "phone", "preferred_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": CALC_NAME,
            "description": CALC_DESC,
            "parameters": {
                "type": "object",
                "properties": {
                    "property_price": {
                        "type": "number",
                        "description": "Total purchase price of the property",
                    },
                    "down_payment": {
                        "type": "number",
                        "description": "Upfront down payment amount",
                    },
                    "annual_interest_rate": {
                        "type": "number",
                        "description": "Annual interest rate as percentage (e.g. 5.5 for 5.5%)",
                    },
                    "term_years": {
                        "type": "integer",
                        "description": "Mortgage duration in years (e.g. 20 or 25)",
                    },
                    "currency": {
                        "type": "string",
                        "description": "Currency code (default 'AED')",
                    },
                },
                "required": ["property_price", "down_payment", "annual_interest_rate", "term_years"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": CATALOG_NAME,
            "description": CATALOG_DESC,
            "parameters": {
                "type": "object",
                "properties": {
                    "min_price": {
                        "type": "number",
                        "description": "Minimum property price filter",
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maximum property price filter",
                    },
                    "location": {
                        "type": "string",
                        "description": "Area, neighborhood, or city (e.g. 'Downtown', 'Dubai Marina', 'Amman')",
                    },
                    "bedrooms": {
                        "type": "integer",
                        "description": "Number of bedrooms required",
                    },
                    "property_type": {
                        "type": "string",
                        "enum": ["apartment", "villa", "townhouse", "penthouse", "commercial", "land"],
                        "description": "Category of property",
                    },
                    "listing_type": {
                        "type": "string",
                        "enum": ["sale", "rent"],
                        "description": "Buy (sale) or rent",
                    },
                },
                "required": [],
            },
        },
    },
]


# ── Execution Dispatcher  

async def dispatch_tool_call(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> dict[str, Any]:
    """Safely dispatches a tool call with multi-tenant context injection."""
    logger.info("Executing tool '%s' for tenant=%s conv=%s", tool_name, tenant_id, conversation_id)

    if tool_name == BOOKING_NAME:
        pref_time_raw = arguments.get("preferred_time")
        if isinstance(pref_time_raw, str):
            try:
                pref_time = datetime.fromisoformat(pref_time_raw.replace("Z", "+00:00"))
            except ValueError:
                pref_time = datetime.now(timezone.utc)
        else:
            pref_time = pref_time_raw or datetime.now(timezone.utc)

        result = await schedule_viewing(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            visitor_name=str(arguments.get("visitor_name", "Visitor")),
            phone=str(arguments.get("phone", "")),
            preferred_time=pref_time,
            property_ref=arguments.get("property_ref"),
            email=arguments.get("email"),
        )
        return {
            "success": True,
            "tool_name": tool_name,
            "data": result.model_dump(mode="json"),
            "display_message": result.confirmation_message,
        }

    elif tool_name == CALC_NAME:
        quote = calculate_mortgage_tool(
            property_price=Decimal(str(arguments["property_price"])),
            down_payment=Decimal(str(arguments["down_payment"])),
            annual_interest_rate=float(arguments["annual_interest_rate"]),
            term_years=int(arguments["term_years"]),
            currency=str(arguments.get("currency", "AED")),
        )
        return {
            "success": True,
            "tool_name": tool_name,
            "data": quote.model_dump(mode="json", exclude={"schedule"}),
            "display_message": quote.summary_message,
        }

    elif tool_name == CATALOG_NAME:
        p_type = PropertyType(arguments["property_type"]) if arguments.get("property_type") else None
        l_type = PropertyListingType(arguments["listing_type"]) if arguments.get("listing_type") else None
        min_p = Decimal(str(arguments["min_price"])) if arguments.get("min_price") is not None else None
        max_p = Decimal(str(arguments["max_price"])) if arguments.get("max_price") is not None else None

        catalog_resp = await query_property_catalog(
            tenant_id=tenant_id,
            min_price=min_p,
            max_price=max_p,
            location=arguments.get("location"),
            bedrooms=arguments.get("bedrooms"),
            property_type=p_type,
            listing_type=l_type,
            limit=5,
        )
        return {
            "success": True,
            "tool_name": tool_name,
            "data": catalog_resp.model_dump(mode="json"),
            "display_message": catalog_resp.summary_message,
        }

    else:
        raise ValueError(f"Unknown tool '{tool_name}' requested.")