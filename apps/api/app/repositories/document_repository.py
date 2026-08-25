from uuid import UUID

from sqlalchemy import Float, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentChunk, RetrievalLog


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_document(
        self,
        *,
        business_id: UUID,
        title: str,
        document_type: str,
        language: str | None,
        uploaded_by: UUID,
    ) -> Document:
        document = Document(
            business_id=business_id,
            title=title,
            document_type=document_type,
            language=language,
            uploaded_by=uploaded_by,
            status="PENDING",
        )
        self.session.add(document)
        await self.session.flush()
        return document

    async def add_chunk(
        self,
        *,
        document_id: UUID,
        business_id: UUID,
        chunk_text: str,
        page_number: int | None,
        embedding: list[float],
    ) -> DocumentChunk:
        chunk = DocumentChunk(
            document_id=document_id,
            business_id=business_id,
            chunk_text=chunk_text,
            page_number=page_number,
            embedding=embedding,
        )
        self.session.add(chunk)
        await self.session.flush()
        return chunk

    async def get_document(
        self,
        *,
        business_id: UUID,
        document_id: UUID,
    ) -> Document | None:
        result = await self.session.execute(
            select(Document)
            .where(
                Document.id == document_id,
                Document.business_id == business_id,
            )
            .options(selectinload(Document.chunks))
        )
        return result.scalar_one_or_none()

    async def list_documents(self, *, business_id: UUID) -> list[Document]:
        result = await self.session.execute(
            select(Document)
            .where(Document.business_id == business_id)
            .options(selectinload(Document.chunks))
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def similarity_search(
        self, *, business_id: UUID, query_embedding: list[float], top_k: int
    ) -> list[tuple[DocumentChunk, float]]:
        """The actual retrieval step: pgvector's `<=>` operator computes
        cosine DISTANCE (0 = identical, 2 = opposite) directly in SQL, so
        the nearest-neighbor ranking happens in the database, not in
        Python. business_id is filtered here — same tenant-isolation rule
        as every other query in this codebase, just applied to vector
        search instead of a normal WHERE clause.

        Returns (chunk, similarity) pairs, where similarity = 1 - distance
        (so 1.0 = identical, higher = more relevant, matching how a
        person reading the API response would expect "score" to work).
        """
        distance = DocumentChunk.embedding.op("<=>", return_type=Float)(query_embedding)
        result = await self.session.execute(
            select(DocumentChunk, distance.label("distance"))
            .where(
                DocumentChunk.business_id == business_id,
                DocumentChunk.embedding.is_not(None),
            )
            .options(selectinload(DocumentChunk.document))
            .order_by(distance)
            .limit(top_k)
        )
        return [(chunk, 1.0 - dist) for chunk, dist in result.all()]

    async def log_retrieval(
        self,
        *,
        business_id: UUID,
        query: str,
        retrieved_chunk_ids: list[UUID],
        response_id: UUID | None,
    ) -> RetrievalLog:
        log = RetrievalLog(
            business_id=business_id,
            query=query,
            retrieved_chunk_ids=retrieved_chunk_ids,
            response_id=response_id,
        )
        self.session.add(log)
        await self.session.flush()
        return log
