import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    preferred_language: Mapped[str] = mapped_column(String(20), default="en")

    memberships: Mapped[list["BusinessMember"]] = relationship(back_populates="user")


class Business(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "businesses"

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    type: Mapped[str | None] = mapped_column(String(80))
    location: Mapped[str | None] = mapped_column(String(255))
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    settings_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    members: Mapped[list["BusinessMember"]] = relationship(back_populates="business")


class BusinessMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "business_members"
    __table_args__ = (UniqueConstraint("business_id", "user_id", name="uq_business_user"),)

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(30), default="owner")  # owner, staff, mentor, consultant
    status: Mapped[str] = mapped_column(String(20), default="active")

    business: Mapped["Business"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")
