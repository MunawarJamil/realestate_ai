import pytest
from decimal import Decimal
from datetime import datetime, timezone
from app.modules.calculator.schemas import MortgageInput
from app.modules.calculator.engine import calculate_mortgage
from app.modules.calculator.tool import calculate_mortgage_tool

def test_mortgage_calculation_basic():
    inp = MortgageInput(
        property_price=Decimal("1000000"),
        down_payment=Decimal("200000"),
        annual_interest_rate=5.0,
        term_years=25,
        currency="AED",
    )
    res = calculate_mortgage(inp)
    assert res.loan_amount == Decimal("800000")
    assert res.down_payment_pct == 20.0
    assert res.monthly_emi > Decimal("4000")
    assert "AED" in res.summary_message

def test_mortgage_tool_wrapper():
    res = calculate_mortgage_tool(
        property_price=Decimal("2000000"),
        down_payment=Decimal("400000"),
        annual_interest_rate=4.5,
        term_years=20,
    )
    assert res.loan_amount == Decimal("1600000")
    assert "20 years" in res.summary_message