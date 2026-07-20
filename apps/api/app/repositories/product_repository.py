from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, StockMovement


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, business_id: UUID, **fields) -> Product:
        product = Product(business_id=business_id, **fields)
        self.session.add(product)
        await self.session.flush()
        return product

    async def get_by_id(self, *, business_id: UUID, product_id: UUID) -> Product | None:
        """Tenant-scoped fetch. Always filter by business_id -> never trust
        a product_id alone, per the tenant isolation rule in the HLD/LLD."""
        result = await self.session.execute(
            select(Product).where(Product.id == product_id, Product.business_id == business_id)
        )
        return result.scalar_one_or_none()

    async def get_for_update(self, *, business_id: UUID, product_id: UUID) -> Product | None:
        """SELECT ... FOR UPDATE — locks the row so concurrent stock
        adjustments on the same product serialize instead of racing.
        Mirrors the LLD's recordSaleWorkflow pseudocode."""
        result = await self.session.execute(
            select(Product)
            .where(Product.id == product_id, Product.business_id == business_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, *, business_id: UUID, name: str) -> Product | None:
        result = await self.session.execute(
            select(Product).where(Product.business_id == business_id, Product.name == name)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        business_id: UUID,
        category: str | None = None,
        is_active: bool | None = True,
        low_stock_only: bool = False,
    ) -> list[Product]:
        query = select(Product).where(Product.business_id == business_id)
        if category is not None:
            query = query.where(Product.category == category)
        if is_active is not None:
            query = query.where(Product.is_active == is_active)
        if low_stock_only:
            query = query.where(Product.stock_quantity <= Product.reorder_level)
        query = query.order_by(Product.name)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def add_stock_movement(
        self,
        *,
        business_id: UUID,
        product_id: UUID,
        movement_type: str,
        quantity,
        reference_type: str,
        reference_id: UUID | None,
    ) -> StockMovement:
        movement = StockMovement(
            business_id=business_id,
            product_id=product_id,
            movement_type=movement_type,
            quantity=quantity,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        self.session.add(movement)
        await self.session.flush()
        return movement
