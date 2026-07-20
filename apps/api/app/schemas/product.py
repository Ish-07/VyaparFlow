from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ProductCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str | None = None
    unit: str = "piece"
    cost_price: Decimal = Decimal("0")
    selling_price: Decimal = Decimal("0")
    stock_quantity: Decimal = Decimal("0")
    reorder_level: Decimal = Decimal("0")

    @field_validator("cost_price", "selling_price", "stock_quantity", "reorder_level")
    @classmethod
    def non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("must be non-negative")
        return v


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: str | None = None
    unit: str | None = None
    cost_price: Decimal | None = None
    selling_price: Decimal | None = None
    reorder_level: Decimal | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: UUID
    name: str
    category: str | None
    unit: str
    cost_price: Decimal
    selling_price: Decimal
    stock_quantity: Decimal
    reorder_level: Decimal
    is_active: bool
    is_low_stock: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StockAdjustRequest(BaseModel):
    """quantity_change is signed: positive adds stock, negative deducts it.
    e.g. selling 5 units -> quantity_change = -5.
    """

    quantity_change: Decimal = Field(..., description="Positive to add stock, negative to deduct")
    reason: str | None = None
    reference_type: str = "manual"  # manual, sale, purchase, correction
    reference_id: UUID | None = None
    confirm_negative_stock: bool = False

    @field_validator("quantity_change")
    @classmethod
    def not_zero(cls, v: Decimal) -> Decimal:
        if v == 0:
            raise ValueError("quantity_change cannot be zero")
        return v


class StockMovementResponse(BaseModel):
    id: UUID
    product_id: UUID
    movement_type: str
    quantity: Decimal
    reference_type: str | None
    reference_id: UUID | None
    created_at: datetime

    class Config:
        from_attributes = True


class StockAdjustResponse(BaseModel):
    product: ProductResponse
    movement: StockMovementResponse
