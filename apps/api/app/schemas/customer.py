from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str | None = None


class CustomerResponse(BaseModel):
    id: UUID
    name: str
    phone: str | None
    balance_due: Decimal
    last_purchase_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
