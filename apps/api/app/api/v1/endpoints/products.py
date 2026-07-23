from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import BusinessContext, require_business_context
from app.schemas.product import (
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
    StockAdjustRequest,
    StockAdjustResponse,
)
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    payload: ProductCreateRequest,
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await InventoryService(session).create_product(
        business_id=ctx.business_id, payload=payload, actor_id=ctx.user_id
    )


@router.get("", response_model=list[ProductResponse])
async def list_products(
    category: str | None = Query(default=None),
    is_active: bool | None = Query(default=True),
    low_stock_only: bool = Query(default=False),
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await InventoryService(session).list_products(
        business_id=ctx.business_id,
        category=category,
        is_active=is_active,
        low_stock_only=low_stock_only,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await InventoryService(session).get_product(
        business_id=ctx.business_id, product_id=product_id
    )


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    payload: ProductUpdateRequest,
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await InventoryService(session).update_product(
        business_id=ctx.business_id, product_id=product_id, payload=payload
    )


@router.patch("/{product_id}/stock", response_model=StockAdjustResponse)
async def adjust_stock(
    product_id: UUID,
    payload: StockAdjustRequest,
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await InventoryService(session).adjust_stock(
        business_id=ctx.business_id, product_id=product_id, payload=payload, actor_id=ctx.user_id
    )
