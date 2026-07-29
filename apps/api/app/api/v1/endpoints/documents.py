from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import BusinessContext, require_business_context
from app.schemas.document import (
    DocumentIngestRequest,
    DocumentResponse,
    RAGAnswerResponse,
    RAGQueryRequest,
)
from app.services.rag_service import RAGService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=201)
async def ingest_document(
    payload: DocumentIngestRequest,
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await RAGService(session).ingest_document(
        business_id=ctx.business_id, user_id=ctx.user_id, payload=payload
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await RAGService(session).list_documents(business_id=ctx.business_id)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await RAGService(session).get_document(business_id=ctx.business_id, document_id=document_id)


@router.post("/query", response_model=RAGAnswerResponse)
async def query_documents(
    payload: RAGQueryRequest,
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await RAGService(session).answer_question(
        business_id=ctx.business_id, query=payload.query, top_k=payload.top_k
    )
