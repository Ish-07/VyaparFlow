from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.product import Product
from app.models.transaction import Expense, Transaction


class AnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def sum_sales(self, *, business_id: UUID, start: datetime, end: datetime) -> tuple:
        result = await self.session.execute(
            select(func.count(Transaction.id), func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.business_id == business_id,
                Transaction.type == "SALE",
                Transaction.occurred_at >= start,
                Transaction.occurred_at <= end,
            )
        )
        return result.one()

    async def sum_expenses(self, *, business_id: UUID, start: datetime, end: datetime) -> float:
        result = await self.session.execute(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.business_id == business_id,
                Expense.occurred_at >= start,
                Expense.occurred_at <= end,
            )
        )
        return result.scalar_one()

    async def sales_by_payment_status(
        self, *, business_id: UUID, start: datetime, end: datetime
    ) -> list[tuple]:
        result = await self.session.execute(
            select(
                Transaction.payment_status,
                func.count(Transaction.id),
                func.coalesce(func.sum(Transaction.amount), 0),
            )
            .where(
                Transaction.business_id == business_id,
                Transaction.type == "SALE",
                Transaction.occurred_at >= start,
                Transaction.occurred_at <= end,
            )
            .group_by(Transaction.payment_status)
        )
        return result.all()

    async def low_stock_count(self, *, business_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count(Product.id)).where(
                Product.business_id == business_id,
                Product.is_active.is_(True),
                Product.stock_quantity <= Product.reorder_level,
            )
        )
        return result.scalar_one()

    async def total_customer_dues(self, *, business_id: UUID) -> float:
        result = await self.session.execute(
            select(func.coalesce(func.sum(Customer.balance_due), 0)).where(
                Customer.business_id == business_id
            )
        )
        return result.scalar_one()
