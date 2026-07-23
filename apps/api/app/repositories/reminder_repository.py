from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insight import Reminder


class ReminderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, business_id: UUID, type: str, message: str, due_at) -> Reminder:
        reminder = Reminder(business_id=business_id, type=type, message=message, due_at=due_at)
        self.session.add(reminder)
        await self.session.flush()
        return reminder

    async def get_by_id(self, *, business_id: UUID, reminder_id: UUID) -> Reminder | None:
        result = await self.session.execute(
            select(Reminder).where(
                Reminder.id == reminder_id, Reminder.business_id == business_id
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self, *, business_id: UUID, status: str | None = None, type: str | None = None
    ) -> list[Reminder]:
        query = select(Reminder).where(Reminder.business_id == business_id)
        if status is not None:
            query = query.where(Reminder.status == status)
        if type is not None:
            query = query.where(Reminder.type == type)
        query = query.order_by(Reminder.due_at)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def find_pending_low_stock_for_product(
        self, *, business_id: UUID, product_name: str
    ) -> Reminder | None:
        """Dedup check: the Reminder table has no product_id column, so we
        match on a message prefix we control ourselves (see
        ReminderService._low_stock_message). Documented tradeoff — if the
        schema grows a proper entity link later, swap this for a real FK
        lookup instead of a string prefix match.
        """
        prefix = f"Low stock: {product_name} "
        result = await self.session.execute(
            select(Reminder).where(
                Reminder.business_id == business_id,
                Reminder.type == "low_stock",
                Reminder.status == "PENDING",
                Reminder.message.startswith(prefix),
            )
        )
        return result.scalars().first()
