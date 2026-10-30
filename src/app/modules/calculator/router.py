from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import ValidationError

from app.modules.calculator.engine import calculate_mortgage
from app.modules.calculator.schemas import MortgageInput, MortgageQuote

router = APIRouter(prefix="/calculator", tags=["calculator"])


@router.post(
    "/mortgage",
    response_model=MortgageQuote,
    summary="Calculate mortgage EMI, total interest, and repayment",
)
async def mortgage_calculator(
    body: MortgageInput,
    include_schedule: bool = Query(
        False,
        description="Include full month-by-month amortization schedule in the response",
    ),
) -> MortgageQuote:
    """Stateless mortgage calculator — no authentication required.

    Returns monthly EMI, total interest, total repayment, and an optional
    full amortization schedule.
    """
    try:
        return calculate_mortgage(body, include_schedule=include_schedule)
    except (ValueError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc