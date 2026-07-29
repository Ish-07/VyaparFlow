import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin

# Embedding dimension - MUST match the configured embedding model's actual
# output size exactly (pgvector's column type bakes this in; a mismatch
# fails on insert, not silently). nvidia/nemotron-3-embed-1b outputs
# 2048-dim vectors natively and does NOT support reduced dimensions
# (confirmed against NVIDIA's NIM docs) - this is NOT the OpenAI
# text-embedding-3-small default of 1536 some boilerplate assumes.
EMBEDDING_DIM = 2048


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "documents"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True
    )
    # Nullable: Step 9 ingests pasted/extracted TEXT directly (no object
    # storage wired up yet - that's a separate concern from RAG itself).
    # file_url is populated only when a document actually has a source file.
    file_url: Mapped[str | None] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    document_type: Mapped[str] = mapped_column(String(60), nullable=False)  # invoice, bill, note, scheme, help
    language: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")  # PENDING, PROCESSING, INDEXED, FAILED
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True
    )
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))

    document: Mapped["Document"] = relationship(back_populates="chunks")


class RetrievalLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "retrieval_logs"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_chunk_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    response_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
