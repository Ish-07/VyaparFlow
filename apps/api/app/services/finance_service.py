from datetime import date, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.customer_repository import CustomerRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.transaction_repository import ExpenseRepository, TransactionRepository
from app.schemas.transaction import (
    ExpenseCreateRequest,
    ExpenseResponse,
    SaleCreateRequest,
    TransactionResponse,
)
from app.services.audit_service import AuditLogService
from app.services.inventory_service import enforce_stock_policy
from app.services.reminder_service import ReminderService


class FinanceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.products = ProductRepository(session)
        self.customers = CustomerRepository(session)
        self.transactions = TransactionRepository(session)
        self.expenses = ExpenseRepository(session)
        self.audit = AuditLogService(session)
        self.reminders = ReminderService(session)

    async def record_sale(
        self, *, business_id: UUID, payload: SaleCreateRequest, actor_id: UUID | None = None
    ) -> TransactionResponse:
        """Mirrors the LLD's recordSaleWorkflow: lock every product row,
        validate stock for ALL items before writing anything, then create
        the transaction + items + stock movements + customer due update
        atomically. If any item fails validation, nothing is written —
        the whole request rolls back (single DB transaction, one commit
        at the end).
        """
        # Lock every involved product up front, in a stable order (by id)
        # to avoid deadlocks if two sales touch overlapping product sets.
        product_ids = sorted({item.product_id for item in payload.items}, key=str)
        locked_products = {}
        for pid in product_ids:
            product = await self.products.get_for_update(business_id=business_id, product_id=pid)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product {pid} not found for this business",
                )
            locked_products[pid] = product

        # Validate stock for every line BEFORE mutating anything.
        for item in payload.items:
            product = locked_products[item.product_id]
            enforce_stock_policy(
                product=product,
                quantity_change=-item.quantity,
                confirm_negative_stock=payload.confirm_negative_stock,
            )

        customer = None
        if payload.customer_id is not None:
            customer = await self.customers.get_for_update(
                business_id=business_id, customer_id=payload.customer_id
            )
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found"
                )

        total_amount = sum(item.quantity * item.unit_price for item in payload.items)

        txn = await self.transactions.create_transaction(
            business_id=business_id,
            type="SALE",
            amount=total_amount,
            payment_status=payload.payment_status,
            customer_id=payload.customer_id,
        )

        for item in payload.items:
            product = locked_products[item.product_id]
            line_total = item.quantity * item.unit_price
            await self.transactions.add_item(
                transaction_id=txn.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total=line_total,
            )
            product.stock_quantity = product.stock_quantity - item.quantity
            await self.products.add_stock_movement(
                business_id=business_id,
                product_id=item.product_id,
                movement_type="OUT",
                quantity=item.quantity,
                reference_type="sale",
                reference_id=txn.id,
            )

        if customer is not None:
            # NOTE (documented assumption): the schema tracks a single
            # balance_due, not a separate paid/owed split. For DUE and
            # PARTIAL sales we add the full sale amount to balance_due —
            # there's no amount_paid field yet to record a partial payment
            # precisely. Revisit if partial-payment tracking is needed.
            if payload.payment_status in ("DUE", "PARTIAL"):
                customer.balance_due = customer.balance_due + total_amount
            customer.last_purchase_at = datetime.utcnow()

        for product in locked_products.values():
            await self.reminders.ensure_low_stock_reminder(business_id=business_id, product=product)

        await self.audit.record(
            business_id=business_id,
            actor_type="user",
            actor_id=str(actor_id) if actor_id else None,
            action="sale.recorded",
            entity_type="transaction",
            entity_id=txn.id,
            metadata={
                "amount": float(total_amount),
                "payment_status": payload.payment_status,
                "item_count": len(payload.items),
            },
        )

        await self.session.commit()
        txn = await self.transactions.get_by_id(business_id=business_id, transaction_id=txn.id)
        return TransactionResponse.model_validate(txn)

    async def list_transactions(
        self,
        *,
        business_id: UUID,
        type: str | None,
        payment_status: str | None,
        date_from: date | None,
        date_to: date | None,
    ) -> list[TransactionResponse]:
        txns = await self.transactions.list(
            business_id=business_id,
            type=type,
            payment_status=payment_status,
            date_from=date_from,
            date_to=date_to,
        )
        return [TransactionResponse.model_validate(t) for t in txns]

    async def get_transaction(
        self, *, business_id: UUID, transaction_id: UUID
    ) -> TransactionResponse:
        txn = await self.transactions.get_by_id(
            business_id=business_id, transaction_id=transaction_id
        )
        if not txn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        return TransactionResponse.model_validate(txn)

    async def record_expense(
        self, *, business_id: UUID, payload: ExpenseCreateRequest, actor_id: UUID | None = None
    ) -> ExpenseResponse:
        expense = await self.expenses.create(
            business_id=business_id,
            category=payload.category,
            amount=payload.amount,
            note=payload.note,
        )
        await self.audit.record(
            business_id=business_id,
            actor_type="user",
            actor_id=str(actor_id) if actor_id else None,
            action="expense.recorded",
            entity_type="expense",
            entity_id=expense.id,
            metadata={"category": expense.category, "amount": float(expense.amount)},
        )
        await self.session.commit()
        await self.session.refresh(expense)
        return ExpenseResponse.model_validate(expense)

    async def list_expenses(
        self,
        *,
        business_id: UUID,
        category: str | None,
        date_from: date | None,
        date_to: date | None,
    ) -> list[ExpenseResponse]:
        expenses = await self.expenses.list(
            business_id=business_id, category=category, date_from=date_from, date_to=date_to
        )
        return [ExpenseResponse.model_validate(e) for e in expenses]
