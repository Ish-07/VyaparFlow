from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import BusinessContext, require_business_context
from app.schemas.voice_command import (
    VoiceCommandConfirmRequest,
    VoiceCommandCreateRequest,
    VoiceCommandResponse,
)
from app.services.voice_command_service import VoiceCommandService

router = APIRouter(prefix="/voice-commands", tags=["voice-commands"])


@router.post("", response_model=VoiceCommandResponse, status_code=201)
async def create_voice_command(
    payload: VoiceCommandCreateRequest,
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await VoiceCommandService(session).create_command(
        business_id=ctx.business_id, user_id=ctx.user_id, payload=payload
    )


@router.get("", response_model=list[VoiceCommandResponse])
async def list_voice_commands(
    status: str | None = Query(default=None),
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await VoiceCommandService(session).list_commands(
        business_id=ctx.business_id, status_filter=status
    )


@router.get("/{command_id}", response_model=VoiceCommandResponse)
async def get_voice_command(
    command_id: UUID,
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await VoiceCommandService(session).get_command(
        business_id=ctx.business_id, command_id=command_id
    )


@router.post("/{command_id}/confirm", response_model=VoiceCommandResponse)
async def confirm_voice_command(
    command_id: UUID,
    payload: VoiceCommandConfirmRequest,
    ctx: BusinessContext = Depends(require_business_context),
    session: AsyncSession = Depends(get_session),
):
    return await VoiceCommandService(session).confirm_command(
        business_id=ctx.business_id, user_id=ctx.user_id, command_id=command_id, payload=payload
    )
