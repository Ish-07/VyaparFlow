"""Password hashing and JWT helpers.

Kept deliberately separate from business logic (services/) so auth
primitives can be unit-tested and reused without pulling in the DB.
"""
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return _pwd_context.verify(plain_password, password_hash)


def create_access_token(
    *,
    user_id: UUID,
    business_id: UUID | None = None,
    role: str | None = None,
    expires_minutes: int | None = None,
) -> str:
    """Issue a JWT.

    business_id/role are only included once a business context has been
    selected (see auth flow: login -> [maybe] select-business). Downstream
    endpoints use `require_business_context` to enforce that a scoped
    token is present before touching business-owned data.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",
    }
    if business_id is not None:
        payload["business_id"] = str(business_id)
    if role is not None:
        payload["role"] = role
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises jose.JWTError on invalid/expired tokens; caller maps to HTTP 401."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "JWTError",
]
