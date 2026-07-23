from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import BusinessContext, require_business_context
from app.schemas.transaction import ExpenseCreateRequest, ExpenseResponse
from app.services.finance_service import FinanceService

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("", response_model=ExpenseResponse, status_code=201)
async def record_expense(
    payload: ExpenseCreateRequest,
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await FinanceService(session).record_expense(
        business_id=ctx.business_id, payload=payload, actor_id=ctx.user_id
    )


@router.get("", response_model=list[ExpenseResponse])
async def list_expenses(
    category: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await FinanceService(session).list_expenses(
        business_id=ctx.business_id, category=category, date_from=date_from, date_to=date_to
    )
