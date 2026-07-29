import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class VoiceCommand(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "voice_commands"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    input_type: Mapped[str] = mapped_column(String(20), nullable=False)  # audio, text
    transcript: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(20))
    intent: Mapped[str | None] = mapped_column(String(40))  # SALE, EXPENSE, STOCK_UPDATE, REPORT, UNKNOWN
    entities: Mapped[dict] = mapped_column(JSONB, default=dict)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    # PENDING, TRANSCRIBING, UNDERSTANDING, EXECUTING, NEEDS_CONFIRMATION, COMPLETED, FAILED
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    final_response: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column()


class AgentTask(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "agent_tasks"

    command_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voice_commands.id"), nullable=False, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(60), nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")  # PENDING, SUCCESS, FAILED
    input_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_json: Mapped[dict] = mapped_column(JSONB, default=dict)
