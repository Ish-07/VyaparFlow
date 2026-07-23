from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ReminderType = Literal["low_stock", "customer_due", "supplier", "custom"]
ReminderStatus = Literal["PENDING", "SENT", "DISMISSED"]


class ReminderCreateRequest(BaseModel):
    type: ReminderType
    message: str = Field(min_length=1, max_length=1000)
    due_at: datetime


class ReminderStatusUpdateRequest(BaseModel):
    status: ReminderStatus


class ReminderResponse(BaseModel):
    id: UUID
    type: str
    message: str
    due_at: datetime
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
