import uuid

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class Product(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("business_id", "name", name="uq_business_product_name"),)

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str | None] = mapped_column(String(80))
    unit: Mapped[str] = mapped_column(String(30), default="piece")
    cost_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    selling_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    stock_quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    reorder_level: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class StockMovement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "stock_movements"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )
    movement_type: Mapped[str] = mapped_column(String(20))  # IN, OUT, ADJUSTMENT
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(30))  # sale, purchase, manual
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
