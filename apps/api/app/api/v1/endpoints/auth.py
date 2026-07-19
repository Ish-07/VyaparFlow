from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import get_current_user
from app.models import User
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    SelectBusinessRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(payload: UserRegisterRequest, session: AsyncSession = Depends(get_session)):
    return await AuthService(session).register(payload)


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)):
    return await AuthService(session).login(payload)


@router.post("/select-business", response_model=LoginResponse)
async def select_business(
    payload: SelectBusinessRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await AuthService(session).select_business(user=user, business_id=payload.business_id)


@router.get("/me", response_model=CurrentUserResponse)
async def me(user: User = Depends(get_current_user)):
    payload = getattr(user, "_token_payload", {})
    return CurrentUserResponse(
        user=UserResponse.model_validate(user),
        business_id=payload.get("business_id"),
        role=payload.get("role"),
    )
