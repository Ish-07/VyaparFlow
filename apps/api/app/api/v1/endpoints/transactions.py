from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import BusinessContext, require_business_context
from app.schemas.transaction import SaleCreateRequest, TransactionResponse
from app.services.finance_service import FinanceService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/sale", response_model=TransactionResponse, status_code=201)
async def record_sale(
    payload: SaleCreateRequest,
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await FinanceService(session).record_sale(
        business_id=ctx.business_id, payload=payload, actor_id=ctx.user_id
    )


@router.get("", response_model=list[TransactionResponse])
async def list_transactions(
    type: str | None = Query(default=None),
    payment_status: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await FinanceService(session).list_transactions(
        business_id=ctx.business_id,
        type=type,
        payment_status=payment_status,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: UUID,
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await FinanceService(session).get_transaction(
        business_id=ctx.business_id, transaction_id=transaction_id
    )
