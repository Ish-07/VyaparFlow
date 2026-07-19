from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.repositories.business_repository import BusinessRepository
from app.schemas.business import BusinessCreateRequest, BusinessResponse


class BusinessService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.businesses = BusinessRepository(session)

    async def create_business(self, *, user: User, payload: BusinessCreateRequest) -> BusinessResponse:
        business = await self.businesses.create_business(
            owner_user_id=user.id,
            name=payload.name,
            type=payload.type,
            location=payload.location,
            currency=payload.currency,
        )
        await self.businesses.add_member(
            business_id=business.id, user_id=user.id, role="owner", status="active"
        )
        await self.session.commit()
        return BusinessResponse(
            id=business.id,
            name=business.name,
            type=business.type,
            location=business.location,
            currency=business.currency,
            role="owner",
            created_at=business.created_at,
        )
