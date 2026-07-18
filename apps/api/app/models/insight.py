import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class Insight(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "insights"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True
    )
    insight_type: Mapped[str] = mapped_column(String(60), nullable=False)  # pricing, trend, forecast, weekly_summary
    message: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))


class Reminder(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "reminders"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(40), nullable=False)  # low_stock, customer_due, supplier, custom
    message: Mapped[str] = mapped_column(Text, nullable=False)
    due_at: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING, SENT, DISMISSED
