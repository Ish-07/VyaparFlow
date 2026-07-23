from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import BusinessContext, require_business_context
from app.repositories.product_repository import ProductRepository
from app.schemas.reminder import (
    ReminderCreateRequest,
    ReminderResponse,
    ReminderStatusUpdateRequest,
)
from app.services.reminder_service import ReminderService

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.post("", response_model=ReminderResponse, status_code=201)
async def create_reminder(
    payload: ReminderCreateRequest,
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await ReminderService(session).create_reminder(
        business_id=ctx.business_id, payload=payload
    )


@router.get("", response_model=list[ReminderResponse])
async def list_reminders(
    status_filter: str | None = Query(default=None, alias="status"),
    type: str | None = Query(default=None),
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await ReminderService(session).list_reminders(
        business_id=ctx.business_id, status_filter=status_filter, type=type
    )


@router.patch("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder_status(
    reminder_id: UUID,
    payload: ReminderStatusUpdateRequest,
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await ReminderService(session).update_status(
        business_id=ctx.business_id, reminder_id=reminder_id, new_status=payload.status
    )


@router.post("/check-low-stock", response_model=list[ReminderResponse], status_code=201)
async def check_low_stock(
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    """Manual trigger for a full low-stock scan across all products —
    useful for an initial sweep or a scheduled job. Individual sales and
    stock adjustments already trigger this automatically for the specific
    product involved (see InventoryService/FinanceService).
    """
    products = await ProductRepository(session).list(business_id=ctx.business_id, low_stock_only=True)
    service = ReminderService(session)
    for product in products:
        await service.ensure_low_stock_reminder(business_id=ctx.business_id, product=product)
        await session.commit()
    return await service.list_reminders(business_id=ctx.business_id, status_filter="PENDING", type="low_stock")
