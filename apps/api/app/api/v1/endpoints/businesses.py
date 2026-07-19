from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import get_current_user
from app.models import User
from app.repositories.business_repository import BusinessRepository
from app.schemas.business import BusinessCreateRequest, BusinessResponse
from app.services.business_service import BusinessService

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("", response_model=BusinessResponse, status_code=201)
async def create_business(
    payload: BusinessCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Onboarding endpoint: creates a business and makes the caller its owner.
    A user with zero memberships hits this after login (needs_onboarding=True),
    then calls /auth/select-business (or logs in again) to get a scoped token.
    """
    return await BusinessService(session).create_business(user=user, payload=payload)


@router.get("", response_model=list[BusinessResponse])
async def list_my_businesses(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    memberships = await BusinessRepository(session).list_memberships_for_user(user.id)
    return [
        BusinessResponse(
            id=m.business.id,
            name=m.business.name,
            type=m.business.type,
            location=m.business.location,
            currency=m.business.currency,
            role=m.role,
            created_at=m.business.created_at,
        )
        for m in memberships
    ]
