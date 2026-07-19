"""Shared FastAPI dependencies for auth and tenant context.

Every business-owned endpoint built from here on should depend on
`require_business_context` (not just `get_current_user`), per the
HLD/LLD rule that every query and service method must filter on
business_id for tenant isolation.
"""
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import JWTError, decode_access_token
from app.models import User
from app.repositories.user_repository import UserRepository

_bearer_scheme = HTTPBearer(auto_error=True)


class BusinessContext:
    """Resolved tenant context attached to a request: which business, which role."""

    def __init__(self, business_id: UUID, role: str):
        self.business_id = business_id
        self.role = role


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await UserRepository(session).get_by_id(UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Stash the raw payload so `require_business_context` doesn't need to
    # decode the token a second time.
    user._token_payload = payload  # type: ignore[attr-defined]
    return user


async def require_business_context(
    user: User = Depends(get_current_user),
) -> BusinessContext:
    """Use this (instead of get_current_user alone) on any endpoint that
    reads or writes business-owned data. Raises 400 if the caller's token
    isn't scoped to a business yet (multi-business users must call
    /auth/select-business first; brand-new users must finish onboarding).
    """
    payload = getattr(user, "_token_payload", {})
    business_id = payload.get("business_id")
    role = payload.get("role")
    if not business_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No business selected for this session. Call /auth/select-business "
            "or complete business onboarding first.",
        )
    return BusinessContext(business_id=UUID(business_id), role=role)
