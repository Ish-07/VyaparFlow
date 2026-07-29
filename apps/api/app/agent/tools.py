"""
Safe tool wrappers for agent nodes.

Per the project's own design rule ("agents plan workflows; domain
services validate and write data"), agent nodes NEVER call repositories
or the DB session directly — they only call these tool functions, which
delegate to the same InventoryService/FinanceService/etc. that the
regular REST endpoints use. This means a bug or a bad LLM output in the
agent layer literally cannot bypass stock policy, tenant scope, or
transaction integrity: those checks live one layer down, in services
that this layer has no way around.
"""
from uuid import UUID

from app.repositories.insight_repository import InsightRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product import StockAdjustRequest
from app.schemas.transaction import ExpenseCreateRequest, SaleCreateRequest, SaleItemRequest
from app.services.finance_service import FinanceService
from app.services.inventory_service import InventoryService


async def tool_find_product(session, *, business_id: UUID, product_name: str):
    """Case-insensitive product lookup with a naive singular/plural
    fallback — see nlp_service.py's docstring on deferring real fuzzy
    matching to the RAG/embeddings step."""
    products = ProductRepository(session)
    product = await products.find_by_name_ilike(business_id=business_id, name=product_name)
    if not product and product_name.endswith("s"):
        product = await products.find_by_name_ilike(business_id=business_id, name=product_name[:-1])
    return product


async def tool_get_product(session, *, business_id: UUID, product_id: UUID):
    return await ProductRepository(session).get_by_id(business_id=business_id, product_id=product_id)


async def tool_record_sale(
    session,
    *,
    business_id: UUID,
    actor_id: UUID,
    product_id: UUID,
    quantity: float,
    unit_price: float,
    payment_status: str = "PAID",
    customer_id: UUID | None = None,
    confirm_negative_stock: bool = False,
):
    payload = SaleCreateRequest(
        items=[SaleItemRequest(product_id=product_id, quantity=quantity, unit_price=unit_price)],
        payment_status=payment_status,
        customer_id=customer_id,
        confirm_negative_stock=confirm_negative_stock,
    )
    return await FinanceService(session).record_sale(
        business_id=business_id, payload=payload, actor_id=actor_id
    )


async def tool_record_expense(session, *, business_id: UUID, actor_id: UUID, amount: float, category: str):
    payload = ExpenseCreateRequest(category=category, amount=amount)
    return await FinanceService(session).record_expense(
        business_id=business_id, payload=payload, actor_id=actor_id
    )


async def tool_adjust_stock(
    session,
    *,
    business_id: UUID,
    actor_id: UUID,
    product_id: UUID,
    quantity_change: float,
    reference_type: str = "voice_command",
    confirm_negative_stock: bool = False,
):
    payload = StockAdjustRequest(
        quantity_change=quantity_change,
        reference_type=reference_type,
        confirm_negative_stock=confirm_negative_stock,
    )
    return await InventoryService(session).adjust_stock(
        business_id=business_id, product_id=product_id, payload=payload, actor_id=actor_id
    )


async def tool_create_insight(
    session, *, business_id: UUID, insight_type: str, message: str, confidence: float | None = None
):
    return await InsightRepository(session).create(
        business_id=business_id, insight_type=insight_type, message=message, confidence=confidence
    )
