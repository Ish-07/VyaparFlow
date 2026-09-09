from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import File, Form, UploadFile

from app.services.ocr_service import get_ocr_service

from app.core.database import get_session
from app.core.deps import BusinessContext, require_business_context
from app.schemas.document import (
    DocumentContentResponse,
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

@router.get(
    "/{document_id}/content",
    response_model=DocumentContentResponse,
)
async def get_document_content(
    document_id: UUID,
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await RAGService(session).get_document_content(
        business_id=ctx.business_id,
        document_id=document_id,
    )

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
    business_id=ctx.business_id,
    query=payload.query,
    top_k=payload.top_k,
    document_id=payload.document_id,
)
@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document_for_ocr(
    file: UploadFile = File(...),
    title: str = Form(...),
    document_type: str = Form(default="invoice"),
    language: str | None = Form(default=None),
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    extracted_text = await get_ocr_service().extract_text_from_upload(file)

    payload = DocumentIngestRequest(
        title=title,
        document_type=document_type,
        language=language,
        text=extracted_text,
    )

    return await RAGService(session).ingest_document(
        business_id=ctx.business_id,
        user_id=ctx.user_id,
        payload=payload,
    )