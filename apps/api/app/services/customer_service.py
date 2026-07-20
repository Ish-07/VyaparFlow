from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerCreateRequest, CustomerResponse


class CustomerService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.customers = CustomerRepository(session)

    async def create_customer(
        self, *, business_id: UUID, payload: CustomerCreateRequest
    ) -> CustomerResponse:
        customer = await self.customers.create(
            business_id=business_id, name=payload.name, phone=payload.phone
        )
        await self.session.commit()
        await self.session.refresh(customer)
        return CustomerResponse.model_validate(customer)

    async def list_customers(self, *, business_id: UUID) -> list[CustomerResponse]:
        customers = await self.customers.list(business_id=business_id)
        return [CustomerResponse.model_validate(c) for c in customers]
