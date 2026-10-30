from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from pydantic import BaseModel, Field, model_validator


class MortgageInput(BaseModel):
    """Input payload for the mortgage calculator tool."""

    property_price: Decimal = Field(
        ..., gt=Decimal("0"), description="Total property price"
    )
    down_payment: Decimal = Field(
        ..., gt=Decimal("0"), description="Down payment amount (must be less than property price)"
    )
    annual_interest_rate: float = Field(
        ..., gt=0, le=20.0,
        description="Annual interest rate as a percentage (e.g. 5.5 for 5.5%)"
    )
    term_years: int = Field(
        ..., ge=1, le=50, description="Loan term in years"
    )
    currency: str = Field(default="AED", max_length=10)

    @model_validator(mode="after")
    def validate_down_payment(self) -> MortgageInput:
        if self.down_payment >= self.property_price:
            raise ValueError("down_payment must be less than property_price")
        return self


class AmortizationRow(BaseModel):
    """Single month entry in the amortization schedule."""
    month: int
    opening_balance: Decimal
    principal: Decimal
    interest: Decimal
    closing_balance: Decimal


class MortgageQuote(BaseModel):
    """Full mortgage calculation result returned by the engine and the agentic tool."""

    # ── Inputs echo ──────────────────────────────────────────────────────────
    property_price: Decimal
    down_payment: Decimal
    loan_amount: Decimal
    annual_interest_rate: float
    term_years: int
    currency: str

    # ── Key outputs ──────────────────────────────────────────────────────────
    monthly_emi: Decimal        = Field(description="Equal Monthly Installment")
    total_payment: Decimal      = Field(description="Total amount paid over the full term")
    total_interest: Decimal     = Field(description="Total interest paid over the full term")
    down_payment_pct: float     = Field(description="Down payment as % of property price")

    # ── First-year summary (useful for quick agent responses) ────────────────
    year_one_interest: Decimal  = Field(description="Interest paid in the first 12 months")
    year_one_principal: Decimal = Field(description="Principal repaid in the first 12 months")

    # ── Full amortization schedule (optional, omitted in brief tool responses) ──
    schedule: list[AmortizationRow] = Field(
        default_factory=list,
        description="Month-by-month amortization table (only populated when requested)"
    )

    # ── Human-readable summary for the AI to relay ──────────────────────────
    summary_message: str        = Field(description="Ready-made natural-language summary")