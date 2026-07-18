import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """Every table uses a UUID primary key, generated client-side."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """created_at / updated_at columns, server-managed."""

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


# Note: business_id is declared explicitly on each business-owned model
# (rather than via a mixin) because ForeignKey/index need the concrete
# class in scope. Convention per HLD/LLD: every business-owned table has
# a `business_id` FK to businesses.id, indexed, and every query/service
# method must filter on it for tenant isolation.
