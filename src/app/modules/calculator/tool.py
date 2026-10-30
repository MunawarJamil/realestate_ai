"""
calculate_mortgage: Agentic tool for real estate financial calculations.

This is the callable the LangGraph tool node will invoke.
It is purely synchronous math — no DB, no network, no async required.

Usage by the LangGraph tool executor:
    result = calculate_mortgage_tool(
        property_price=Decimal("1500000"),
        down_payment=Decimal("300000"),
        annual_interest_rate=5.5,
        term_years=25,
        currency="AED",
    )
    # result.summary_message → relay directly to visitor
"""
from __future__ import annotations

from decimal import Decimal

from app.modules.calculator.engine import calculate_mortgage
from app.modules.calculator.schemas import MortgageInput, MortgageQuote

# ── Tool metadata (consumed by the LangGraph tool registry in Phase 14.4) ──────

TOOL_NAME = "calculate_mortgage"
TOOL_DESCRIPTION = (
    "Calculates the monthly mortgage installment (EMI), total interest, and total "
    "repayment for a real estate purchase. Use this tool when the visitor asks about "
    "financing, monthly payments, loan affordability, or mortgage costs. "
    "Always confirm property_price, down_payment, annual_interest_rate, and "
    "term_years before calling."
)


def calculate_mortgage_tool(
    *,
    property_price: Decimal,
    down_payment: Decimal,
    annual_interest_rate: float,
    term_years: int,
    currency: str = "AED",
    include_schedule: bool = False,
) -> MortgageQuote:
    """Agentic tool entry-point — validates inputs via Pydantic then runs the engine.

    Args:
        property_price:        Total listed price of the property.
        down_payment:          Amount the buyer pays upfront.
        annual_interest_rate:  Annual rate as a plain percentage (e.g. 5.5 for 5.5 %).
        term_years:            Repayment period in full years (1 – 50).
        currency:              ISO currency code displayed in outputs (default: AED).
        include_schedule:      Set True to include full amortization table in the result.
                               Keep False (default) for agent chat responses.

    Returns:
        MortgageQuote — the engine's full result including `summary_message`.

    Raises:
        pydantic.ValidationError: If any input fails validation (bad range, etc.).
    """
    validated = MortgageInput(
        property_price=property_price,
        down_payment=down_payment,
        annual_interest_rate=annual_interest_rate,
        term_years=term_years,
        currency=currency,
    )
    return calculate_mortgage(validated, include_schedule=include_schedule)