"""
RAG service.

Ingestion note (deliberate scope decision for this step): there is no
object storage (S3/MinIO) wired into the project yet, so this accepts
already-extracted TEXT directly rather than a file upload. A future step
can add file upload + OCR/PDF-text-extraction in front of this without
changing anything below `ingest_document`'s `text` parameter - chunking,
embedding, and storage are already decoupled from how the text arrived.

Chunking note: fixed-size character chunking with overlap, not
semantic/heading-aware chunking. Documented simplification, consistent
with how earlier steps (e.g. product-name matching) documented similar
"correct but simple" tradeoffs rather than building the fanciest version
first.
"""
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.document_repository import DocumentRepository
from app.schemas.document import (
    DocumentContentResponse,
    DocumentIngestRequest,
    DocumentResponse,
    RAGAnswerResponse,
    RAGSourceChunk,
)
from app.services.ai.base import AIProviderError
from app.services.ai.router import AIRouter

_CHUNK_SIZE = 800
_CHUNK_OVERLAP = 100
_MIN_SIMILARITY_FOR_CONTEXT = 0.3  # below this, a chunk is treated as noise, not real context


def _chunk_text(text: str, *, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def _to_response(document, chunk_count: int) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        title=document.title,
        document_type=document.document_type,
        language=document.language,
        status=document.status,
        chunk_count=chunk_count,
        created_at=document.created_at,
    )


class RAGService:
    def __init__(self, session: AsyncSession, ai_router: AIRouter | None = None):
        self.session = session
        self.documents = DocumentRepository(session)
        self.ai_router = ai_router or AIRouter()

    async def ingest_document(
        self, *, business_id: UUID, user_id: UUID, payload: DocumentIngestRequest
    ) -> DocumentResponse:
        document = await self.documents.create_document(
            business_id=business_id,
            title=payload.title,
            document_type=payload.document_type,
            language=payload.language,
            uploaded_by=user_id,
        )

        chunks = _chunk_text(payload.text)
        if not chunks:
            document.status = "FAILED"
            await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Document text is empty"
            )

        document.status = "PROCESSING"
        await self.session.flush()

        try:
            for chunk_text in chunks:
                # input_type="passage": this is text going INTO the index,
                # not a search query - using the wrong mode here silently
                # degrades retrieval quality (see AIProvider.create_embedding).
                embedding = await self.ai_router.create_embedding(chunk_text, input_type="passage")
                await self.documents.add_chunk(
                    document_id=document.id,
                    business_id=business_id,
                    chunk_text=chunk_text,
                    page_number=None,
                    embedding=embedding,
                )
        except AIProviderError as exc:
            document.status = "FAILED"
            await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not generate embeddings for this document: {exc}",
            )

        document.status = "INDEXED"
        await self.session.commit()
        await self.session.refresh(document)
        return _to_response(document, chunk_count=len(chunks))

    async def list_documents(self, *, business_id: UUID) -> list[DocumentResponse]:
        documents = await self.documents.list_documents(business_id=business_id)
        return [_to_response(d, chunk_count=len(d.chunks)) for d in documents]

    async def get_document(self, *, business_id: UUID, document_id: UUID) -> DocumentResponse:
        document = await self.documents.get_document(business_id=business_id, document_id=document_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return _to_response(document, chunk_count=len(document.chunks))

    async def get_document_content(
    self,
    *,
    business_id: UUID,
    document_id: UUID,
) -> DocumentContentResponse:
        document = await self.documents.get_document(
            business_id=business_id,
            document_id=document_id,
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        ordered_chunks = sorted(
            document.chunks,
            key=lambda chunk: (
                chunk.page_number is None,
                chunk.page_number or 0,
                str(chunk.id),
            ),
        )

        content = "\n\n".join(chunk.chunk_text for chunk in ordered_chunks)

        return DocumentContentResponse(
            id=document.id,
            title=document.title,
            document_type=document.document_type,
            language=document.language,
            status=document.status,
            chunk_count=len(document.chunks),
            created_at=document.created_at,
            content=content,
        )

    async def answer_question(
    self,
    *,
    business_id: UUID,
    query: str,
    top_k: int = 5,
    document_id: UUID | None = None,
) -> RAGAnswerResponse:
        if document_id is not None:
            document = await self.documents.get_document(
                business_id=business_id,
                document_id=document_id,
            )

            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document not found",
                )

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not process this question right now: {exc}",
            ) from exc

        results = await self.documents.similarity_search(
    business_id=business_id,
    query_embedding=query_embedding,
    top_k=top_k,
    document_id=document_id,
)
        relevant = [(chunk, sim) for chunk, sim in results if sim >= _MIN_SIMILARITY_FOR_CONTEXT]

        answer_text, provider_used = await self.ai_router.generate_rag_answer(
            query, [chunk.chunk_text for chunk, _ in relevant]
        )

        await self.documents.log_retrieval(
            business_id=business_id,
            query=query,
            retrieved_chunk_ids=[chunk.id for chunk, _ in relevant],
            response_id=None,
        )

        sources = [
            RAGSourceChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_title=chunk.document.title,
                chunk_text=chunk.chunk_text,
                similarity=round(sim, 4),
            )
            for chunk, sim in relevant
        ]

        return RAGAnswerResponse(
            answer=answer_text,
            sources=sources,
            provider_used=provider_used,
            has_sufficient_context=len(relevant) > 0,
        )

    async def ask_question(
        self,
        *,
        business_id: UUID,
        query: str,
        top_k: int = 5,
    ) -> RAGAnswerResponse:
        return await self.answer_question(business_id=business_id, query=query, top_k=top_k)
