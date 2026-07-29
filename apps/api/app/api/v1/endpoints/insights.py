from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import BusinessContext, require_business_context
from app.repositories.insight_repository import InsightRepository
from app.schemas.insight import InsightResponse

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("", response_model=list[InsightResponse])
async def list_insights(
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    insights = await InsightRepository(session).list(business_id=ctx.business_id)
    return [InsightResponse.model_validate(i) for i in insights]
