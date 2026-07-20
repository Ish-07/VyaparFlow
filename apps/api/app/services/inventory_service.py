from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.product_repository import ProductRepository
from app.schemas.product import (
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
    StockAdjustRequest,
    StockAdjustResponse,
    StockMovementResponse,
)

settings = get_settings()


def _to_response(product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        name=product.name,
        category=product.category,
        unit=product.unit,
        cost_price=product.cost_price,
        selling_price=product.selling_price,
        stock_quantity=product.stock_quantity,
        reorder_level=product.reorder_level,
        is_active=product.is_active,
        is_low_stock=product.stock_quantity <= product.reorder_level,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def enforce_stock_policy(*, product, quantity_change, confirm_negative_stock: bool) -> None:
    """Shared negative-stock policy: used by both direct stock adjustment
    and sale recording, so a sale can't go negative any more permissively
    than a manual stock edit. Raises HTTPException(409) if blocked.
    """
    new_quantity = product.stock_quantity + quantity_change
    if new_quantity < 0 and not settings.allow_negative_stock and not confirm_negative_stock:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": (
                    f"Insufficient stock for '{product.name}': {product.stock_quantity} "
                    f"available, {abs(quantity_change)} requested."
                ),
                "product_id": str(product.id),
                "current_stock": float(product.stock_quantity),
                "requested_deduction": float(abs(quantity_change)),
                "resolution": "Retry with confirm_negative_stock=true to override.",
            },
        )


class InventoryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.products = ProductRepository(session)

    async def create_product(
        self, *, business_id: UUID, payload: ProductCreateRequest
    ) -> ProductResponse:
        existing = await self.products.get_by_name(business_id=business_id, name=payload.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product '{payload.name}' already exists for this business",
            )
        product = await self.products.create(business_id=business_id, **payload.model_dump())
        await self.session.commit()
        return _to_response(product)

    async def list_products(
        self,
        *,
        business_id: UUID,
        category: str | None,
        is_active: bool | None,
        low_stock_only: bool,
    ) -> list[ProductResponse]:
        products = await self.products.list(
            business_id=business_id,
            category=category,
            is_active=is_active,
            low_stock_only=low_stock_only,
        )
        return [_to_response(p) for p in products]

    async def get_product(self, *, business_id: UUID, product_id: UUID) -> ProductResponse:
        product = await self.products.get_by_id(business_id=business_id, product_id=product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        return _to_response(product)

    async def update_product(
        self, *, business_id: UUID, product_id: UUID, payload: ProductUpdateRequest
    ) -> ProductResponse:
        product = await self.products.get_by_id(business_id=business_id, product_id=product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(product, field, value)
        await self.session.commit()
        await self.session.refresh(product)
        return _to_response(product)

    async def adjust_stock(
        self, *, business_id: UUID, product_id: UUID, payload: StockAdjustRequest
    ) -> StockAdjustResponse:
        """Deducting more than available stock is blocked by default (409),
        matching business setting ALLOW_NEGATIVE_STOCK. The caller can
        override per-request with confirm_negative_stock=true, per the
        LLD's 'require explicit confirmation for risky actions' rule.
        """
        # Row lock: two simultaneous sales of the same product must
        # serialize, not both read stale stock and both succeed.
        product = await self.products.get_for_update(
            business_id=business_id, product_id=product_id
        )
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        enforce_stock_policy(
            product=product,
            quantity_change=payload.quantity_change,
            confirm_negative_stock=payload.confirm_negative_stock,
        )
        new_quantity = product.stock_quantity + payload.quantity_change

        product.stock_quantity = new_quantity
        movement_type = "IN" if payload.quantity_change > 0 else "OUT"
        movement = await self.products.add_stock_movement(
            business_id=business_id,
            product_id=product.id,
            movement_type=movement_type,
            quantity=abs(payload.quantity_change),
            reference_type=payload.reference_type,
            reference_id=payload.reference_id,
        )
        await self.session.commit()
        await self.session.refresh(product)

        return StockAdjustResponse(
            product=_to_response(product),
            movement=StockMovementResponse.model_validate(movement),
        )
