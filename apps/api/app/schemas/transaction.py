from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

PaymentStatus = Literal["PAID", "DUE", "PARTIAL"]


class SaleItemRequest(BaseModel):
    product_id: UUID
    quantity: Decimal
    unit_price: Decimal  # required every time, per product decision for this step

    @field_validator("quantity", "unit_price")
    @classmethod
    def positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("must be greater than zero")
        return v


class SaleCreateRequest(BaseModel):
    items: list[SaleItemRequest] = Field(min_length=1)
    payment_status: PaymentStatus
    customer_id: UUID | None = None
    confirm_negative_stock: bool = False


class TransactionItemResponse(BaseModel):
    product_id: UUID
    quantity: Decimal
    unit_price: Decimal
    total: Decimal

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    id: UUID
    type: str
    amount: Decimal
    payment_status: str
    customer_id: UUID | None
    occurred_at: datetime
    items: list[TransactionItemResponse] = []

    class Config:
        from_attributes = True


class ExpenseCreateRequest(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(gt=0)
    note: str | None = Field(default=None, max_length=500)


class ExpenseResponse(BaseModel):
    id: UUID
    category: str
    amount: Decimal
    note: str | None
    occurred_at: datetime

    class Config:
        from_attributes = True
