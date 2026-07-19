from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(
        self, *, name: str, email: str, password_hash: str, preferred_language: str = "en"
    ) -> User:
        user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            preferred_language=preferred_language,
        )
        self.session.add(user)
        await self.session.flush()  # populate user.id without committing yet
        return user
