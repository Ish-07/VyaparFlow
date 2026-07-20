from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.transaction import Expense, Transaction, TransactionItem


class TransactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_transaction(
        self,
        *,
        business_id: UUID,
        type: str,
        amount,
        payment_status: str,
        customer_id: UUID | None,
    ) -> Transaction:
        txn = Transaction(
            business_id=business_id,
            type=type,
            amount=amount,
            payment_status=payment_status,
            customer_id=customer_id,
        )
        self.session.add(txn)
        await self.session.flush()
        return txn

    async def add_item(
        self, *, transaction_id: UUID, product_id: UUID, quantity, unit_price, total
    ) -> TransactionItem:
        item = TransactionItem(
            transaction_id=transaction_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            total=total,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def get_by_id(self, *, business_id: UUID, transaction_id: UUID) -> Transaction | None:
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.id == transaction_id, Transaction.business_id == business_id)
            .options(selectinload(Transaction.items))
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        business_id: UUID,
        type: str | None = None,
        payment_status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[Transaction]:
        query = (
            select(Transaction)
            .where(Transaction.business_id == business_id)
            .options(selectinload(Transaction.items))
        )
        if type is not None:
            query = query.where(Transaction.type == type)
        if payment_status is not None:
            query = query.where(Transaction.payment_status == payment_status)
        if date_from is not None:
            query = query.where(Transaction.occurred_at >= date_from)
        if date_to is not None:
            query = query.where(Transaction.occurred_at <= date_to)
        query = query.order_by(Transaction.occurred_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())


class ExpenseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, *, business_id: UUID, category: str, amount, note: str | None
    ) -> Expense:
        expense = Expense(business_id=business_id, category=category, amount=amount, note=note)
        self.session.add(expense)
        await self.session.flush()
        return expense

    async def list(
        self,
        *,
        business_id: UUID,
        category: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[Expense]:
        query = select(Expense).where(Expense.business_id == business_id)
        if category is not None:
            query = query.where(Expense.category == category)
        if date_from is not None:
            query = query.where(Expense.occurred_at >= date_from)
        if date_to is not None:
            query = query.where(Expense.occurred_at <= date_to)
        query = query.order_by(Expense.occurred_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())
