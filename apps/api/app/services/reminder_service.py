from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.reminder_repository import ReminderRepository
from app.schemas.reminder import ReminderCreateRequest, ReminderResponse


def _low_stock_message(product_name: str, stock_quantity, reorder_level) -> str:
    # Keep the "Low stock: {name} " prefix stable — it's what
    # find_pending_low_stock_for_product matches on for dedup.
    return f"Low stock: {product_name} has {stock_quantity} left (reorder level {reorder_level})"


class ReminderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.reminders = ReminderRepository(session)

    async def create_reminder(
        self, *, business_id: UUID, payload: ReminderCreateRequest
    ) -> ReminderResponse:
        reminder = await self.reminders.create(
            business_id=business_id,
            type=payload.type,
            message=payload.message,
            due_at=payload.due_at,
        )
        await self.session.commit()
        await self.session.refresh(reminder)
        return ReminderResponse.model_validate(reminder)

    async def list_reminders(
        self, *, business_id: UUID, status_filter: str | None, type: str | None
    ) -> list[ReminderResponse]:
        reminders = await self.reminders.list(
            business_id=business_id, status=status_filter, type=type
        )
        return [ReminderResponse.model_validate(r) for r in reminders]

    async def update_status(
        self, *, business_id: UUID, reminder_id: UUID, new_status: str
    ) -> ReminderResponse:
        reminder = await self.reminders.get_by_id(business_id=business_id, reminder_id=reminder_id)
        if not reminder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
        reminder.status = new_status
        await self.session.commit()
        await self.session.refresh(reminder)
        return ReminderResponse.model_validate(reminder)

    async def ensure_low_stock_reminder(self, *, business_id: UUID, product) -> None:
        """Non-committing helper: call this from within Inventory/Finance
        services (after a stock change, before their own commit) so a
        low-stock reminder is created atomically with the sale/adjustment
        that caused it. Deduplicates against any existing PENDING
        low_stock reminder for the same product (see repository docstring
        for why matching is done via message prefix, not a product_id FK).
        """
        if product.stock_quantity > product.reorder_level:
            return
        existing = await self.reminders.find_pending_low_stock_for_product(
            business_id=business_id, product_name=product.name
        )
        if existing:
            return
        await self.reminders.create(
            business_id=business_id,
            type="low_stock",
            message=_low_stock_message(product.name, product.stock_quantity, product.reorder_level),
            due_at=datetime.utcnow() + timedelta(hours=1),
        )
