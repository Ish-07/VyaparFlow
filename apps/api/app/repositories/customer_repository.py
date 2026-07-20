from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer


class CustomerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, business_id: UUID, name: str, phone: str | None) -> Customer:
        customer = Customer(business_id=business_id, name=name, phone=phone)
        self.session.add(customer)
        await self.session.flush()
        return customer

    async def get_for_update(self, *, business_id: UUID, customer_id: UUID) -> Customer | None:
        result = await self.session.execute(
            select(Customer)
            .where(Customer.id == customer_id, Customer.business_id == business_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, *, business_id: UUID, customer_id: UUID) -> Customer | None:
        result = await self.session.execute(
            select(Customer).where(
                Customer.id == customer_id, Customer.business_id == business_id
            )
        )
        return result.scalar_one_or_none()

    async def list(self, *, business_id: UUID) -> list[Customer]:
        result = await self.session.execute(
            select(Customer).where(Customer.business_id == business_id).order_by(Customer.name)
        )
        return list(result.scalars().all())
