"""
Pure stateless mortgage amortization engine.
No I/O, no async — safe to call from anywhere (tool, router, tests).
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.modules.calculator.schemas import (
    AmortizationRow,
    MortgageInput,
    MortgageQuote,
)

_CENT = Decimal("0.01")
_ZERO = Decimal("0")


def calculate_mortgage(
    data: MortgageInput,
    *,
    include_schedule: bool = False,
) -> MortgageQuote:
    """Compute a full mortgage quote from validated MortgageInput.

    Formula (standard reducing-balance amortization):
        r   = annual_interest_rate / (12 * 100)
        n   = term_years * 12
        EMI = P * r * (1+r)^n / ((1+r)^n - 1)

    Args:
        data:             Validated MortgageInput (Pydantic model).
        include_schedule: When True, populate `MortgageQuote.schedule` with
                          the full month-by-month amortization table.
                          Keep False for agent responses to avoid token bloat.

    Returns:
        MortgageQuote with all computed fields populated.
    """
    loan_amount: Decimal = data.property_price - data.down_payment
    n: int = data.term_years * 12
    r: Decimal = Decimal(str(data.annual_interest_rate)) / Decimal("1200")

    # ── EMI calculation ───────────────────────────────────────────────────────
    if r == _ZERO:
        # Edge case: 0 % interest (rare but guard against ZeroDivisionError)
        monthly_emi = (loan_amount / Decimal(n)).quantize(_CENT, ROUND_HALF_UP)
    else:
        compound = (1 + r) ** n
        monthly_emi = (loan_amount * r * compound / (compound - 1)).quantize(
            _CENT, ROUND_HALF_UP
        )

    total_payment = (monthly_emi * n).quantize(_CENT, ROUND_HALF_UP)
    total_interest = (total_payment - loan_amount).quantize(_CENT, ROUND_HALF_UP)
    down_payment_pct = float(
        (data.down_payment / data.property_price * 100).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )
    )

    # ── Amortization loop (always computed for year-1 summary) ───────────────
    schedule: list[AmortizationRow] = []
    balance = loan_amount
    year_one_interest = _ZERO
    year_one_principal = _ZERO

    for month in range(1, n + 1):
        interest_component = (balance * r).quantize(_CENT, ROUND_HALF_UP)
        principal_component = (monthly_emi - interest_component).quantize(
            _CENT, ROUND_HALF_UP
        )
        # Guard: last payment may be slightly off due to rounding
        if principal_component > balance:
            principal_component = balance
        closing_balance = (balance - principal_component).quantize(
            _CENT, ROUND_HALF_UP
        )

        if month <= 12:
            year_one_interest += interest_component
            year_one_principal += principal_component

        if include_schedule:
            schedule.append(
                AmortizationRow(
                    month=month,
                    opening_balance=balance,
                    principal=principal_component,
                    interest=interest_component,
                    closing_balance=closing_balance,
                )
            )

        balance = closing_balance
        if balance <= _ZERO:
            break

    # ── Human-readable summary for the AI ────────────────────────────────────
    curr = data.currency
    summary = (
        f"For a {curr} {data.property_price:,.2f} property with a "
        f"{curr} {data.down_payment:,.2f} down payment ({down_payment_pct:.1f}%), "
        f"your loan of {curr} {loan_amount:,.2f} over {data.term_years} years "
        f"at {data.annual_interest_rate:.2f}% p.a. gives a monthly installment of "
        f"**{curr} {monthly_emi:,.2f}**. "
        f"You will pay {curr} {total_interest:,.2f} in total interest, "
        f"bringing your total repayment to {curr} {total_payment:,.2f}."
    )

    return MortgageQuote(
        property_price=data.property_price,
        down_payment=data.down_payment,
        loan_amount=loan_amount,
        annual_interest_rate=data.annual_interest_rate,
        term_years=data.term_years,
        currency=curr,
        monthly_emi=monthly_emi,
        total_payment=total_payment,
        total_interest=total_interest,
        down_payment_pct=down_payment_pct,
        year_one_interest=year_one_interest.quantize(_CENT, ROUND_HALF_UP),
        year_one_principal=year_one_principal.quantize(_CENT, ROUND_HALF_UP),
        schedule=schedule,
        summary_message=summary,
    )