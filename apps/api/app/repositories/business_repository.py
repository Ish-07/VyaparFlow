from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.business import Business, BusinessMember


class BusinessRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_business(
        self,
        *,
        owner_user_id: UUID,
        name: str,
        type: str | None,
        location: str | None,
        currency: str,
    ) -> Business:
        business = Business(
            owner_user_id=owner_user_id,
            name=name,
            type=type,
            location=location,
            currency=currency,
        )
        self.session.add(business)
        await self.session.flush()
        return business

    async def add_member(
        self, *, business_id: UUID, user_id: UUID, role: str = "owner", status: str = "active"
    ) -> BusinessMember:
        member = BusinessMember(
            business_id=business_id, user_id=user_id, role=role, status=status
        )
        self.session.add(member)
        await self.session.flush()
        return member

    async def list_memberships_for_user(self, user_id: UUID) -> list[BusinessMember]:
        """Returns active memberships with their Business eagerly available."""
        result = await self.session.execute(
            select(BusinessMember)
            .where(BusinessMember.user_id == user_id, BusinessMember.status == "active")
            .options(selectinload(BusinessMember.business))
        )
        return list(result.scalars().all())

    async def get_membership(self, *, business_id: UUID, user_id: UUID) -> BusinessMember | None:
        result = await self.session.execute(
            select(BusinessMember).where(
                BusinessMember.business_id == business_id,
                BusinessMember.user_id == user_id,
                BusinessMember.status == "active",
            )
        )
        return result.scalar_one_or_none()
