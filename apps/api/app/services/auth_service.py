from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.repositories.business_repository import BusinessRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    BusinessMembershipSummary,
    LoginRequest,
    LoginResponse,
    UserRegisterRequest,
    UserResponse,
)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.businesses = BusinessRepository(session)

    async def register(self, payload: UserRegisterRequest) -> UserResponse:
        existing = await self.users.get_by_email(payload.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )
        user = await self.users.create(
            name=payload.name,
            email=payload.email,
            password_hash=hash_password(payload.password),
            preferred_language=payload.preferred_language,
        )
        await self.session.commit()
        return UserResponse.model_validate(user)

    async def login(self, payload: LoginRequest) -> LoginResponse:
        user = await self.users.get_by_email(payload.email)
        if not user or not user.password_hash or not verify_password(
            payload.password, user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
            )

        memberships = await self.businesses.list_memberships_for_user(user.id)
        business_summaries = [
            BusinessMembershipSummary(
                business_id=m.business_id, business_name=m.business.name, role=m.role
            )
            for m in memberships
        ]

        # Business-selection rule:
        #  - exactly one active membership -> auto-select it, token is fully scoped
        #  - multiple memberships -> return the list, frontend prompts a picker,
        #    token issued WITHOUT business_id (caller must call /select-business next)
        #  - zero memberships -> needs_onboarding, token issued without business_id
        selected_business_id: UUID | None = None
        role: str | None = None
        needs_onboarding = False

        if len(memberships) == 1:
            selected_business_id = memberships[0].business_id
            role = memberships[0].role
        elif len(memberships) == 0:
            needs_onboarding = True

        token = create_access_token(
            user_id=user.id, business_id=selected_business_id, role=role
        )

        return LoginResponse(
            access_token=token,
            user=UserResponse.model_validate(user),
            businesses=business_summaries,
            selected_business_id=selected_business_id,
            needs_onboarding=needs_onboarding,
        )

    async def select_business(self, *, user: User, business_id: UUID) -> LoginResponse:
        membership = await self.businesses.get_membership(
            business_id=business_id, user_id=user.id
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this business",
            )

        memberships = await self.businesses.list_memberships_for_user(user.id)
        business_summaries = [
            BusinessMembershipSummary(
                business_id=m.business_id, business_name=m.business.name, role=m.role
            )
            for m in memberships
        ]

        token = create_access_token(
            user_id=user.id, business_id=membership.business_id, role=membership.role
        )
        return LoginResponse(
            access_token=token,
            user=UserResponse.model_validate(user),
            businesses=business_summaries,
            selected_business_id=membership.business_id,
            needs_onboarding=False,
        )
