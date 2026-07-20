from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import BusinessContext, require_business_context
from app.schemas.customer import CustomerCreateRequest, CustomerResponse
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(
    payload: CustomerCreateRequest,
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await CustomerService(session).create_customer(
        business_id=ctx.business_id, payload=payload
    )


@router.get("", response_model=list[CustomerResponse])
async def list_customers(
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await CustomerService(session).list_customers(business_id=ctx.business_id)
