from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class VoiceCommandCreateRequest(BaseModel):
    """input_type is always 'text' for now — audio input (Whisper/STT) is
    a later step in the build order; this endpoint already accepts the
    field so the API shape won't need to change when audio is added."""

    input_type: Literal["text"] = "text"
    text: str = Field(min_length=1, max_length=2000)
    idempotency_key: str = Field(min_length=1, max_length=120)


class VoiceCommandConfirmRequest(BaseModel):
    """Used when a command lands in NEEDS_CONFIRMATION — the caller
    supplies/corrects the exact structured fields needed to execute it.
    Which fields are required depends on `intent` (see service docstring).
    """

    product_id: UUID | None = None
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = None
    category: str | None = None
    payment_status: Literal["PAID", "DUE", "PARTIAL"] = "PAID"
    customer_id: UUID | None = None
    confirm_negative_stock: bool = False


class VoiceCommandResponse(BaseModel):
    id: UUID
    input_type: str
    transcript: str | None
    intent: str | None
    entities: dict
    confidence: float | None
    status: str
    final_response: str | None
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True
