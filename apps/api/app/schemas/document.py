from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentIngestRequest(BaseModel):
    """Text-paste ingestion — no object storage exists yet, so this takes
    already-extracted text directly rather than a file upload. See
    rag_service.py's module docstring for the reasoning."""

    title: str = Field(min_length=1, max_length=200)
    document_type: str = Field(default="note", max_length=60)
    language: str | None = None
    text: str = Field(min_length=1, max_length=200_000)


class DocumentResponse(BaseModel):
    id: UUID
    title: str
    document_type: str
    language: str | None
    status: str
    chunk_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class RAGQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)


class RAGSourceChunk(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    chunk_text: str
    similarity: float


class RAGAnswerResponse(BaseModel):
    answer: str
    sources: list[RAGSourceChunk]
    provider_used: str
    has_sufficient_context: bool
