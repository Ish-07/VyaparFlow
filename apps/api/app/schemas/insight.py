from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class InsightResponse(BaseModel):
    id: UUID
    insight_type: str
    message: str
    confidence: float | None
    created_at: datetime

    class Config:
        from_attributes = True
