from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insight import Insight


class InsightRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, *, business_id: UUID, insight_type: str, message: str, confidence: float | None
    ) -> Insight:
        insight = Insight(
            business_id=business_id,
            insight_type=insight_type,
            message=message,
            confidence=confidence,
        )
        self.session.add(insight)
        await self.session.flush()
        return insight

    async def list(self, *, business_id: UUID, limit: int = 50) -> list[Insight]:
        result = await self.session.execute(
            select(Insight)
            .where(Insight.business_id == business_id)
            .order_by(Insight.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
