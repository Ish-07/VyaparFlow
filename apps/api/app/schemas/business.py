from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BusinessCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    type: str | None = None
    location: str | None = None
    currency: str = "INR"


class BusinessResponse(BaseModel):
    id: UUID
    name: str
    type: str | None
    location: str | None
    currency: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True
