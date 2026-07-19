from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    preferred_language: str = "en"


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr | None
    preferred_language: str
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class BusinessMembershipSummary(BaseModel):
    business_id: UUID
    business_name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    businesses: list[BusinessMembershipSummary]
    selected_business_id: UUID | None = None
    needs_onboarding: bool = False


class SelectBusinessRequest(BaseModel):
    business_id: UUID


class CurrentUserResponse(BaseModel):
    user: UserResponse
    business_id: UUID | None = None
    role: str | None = None
