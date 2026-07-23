"""
Test fixtures.

Each test gets its own DB transaction that is rolled back at teardown, so
tests never see each other's data and never need to manually clean up.
This works via SQLAlchemy's join_transaction_mode="create_savepoint":
when app code calls session.commit() (as our services do), it commits to
a SAVEPOINT instead of the real outer transaction — the outer transaction
(and everything nested inside it) is rolled back once the test finishes.

Requires a real Postgres test database. Point TEST_DATABASE_URL at one
that's safe to wipe — never your dev database. Tables are created via
Base.metadata.create_all (bypassing Alembic) purely for test speed;
Alembic itself is verified separately via `alembic check` in each step.
"""
import asyncio
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://vyaparflow@localhost:5432/vyaparflow_test",
    ),
)
os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("ENVIRONMENT", "test")

from app.core.database import Base, get_session  # noqa: E402
from app.main import app  # noqa: E402
from app import models  # noqa: E402,F401  (populate Base.metadata)

TEST_DATABASE_URL = os.environ["DATABASE_URL"]


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    # NullPool is essential here: each pytest-asyncio test function gets
    # its own event loop by default, and asyncpg connections are bound to
    # the loop that created them. A pooled connection reused across a
    # different test's loop crashes with "attached to a different loop".
    # NullPool opens a fresh connection per checkout and closes it
    # immediately after, so nothing loop-bound is ever cached or shared.
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        yield session
        await session.close()
        await conn.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    async def _override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_business(client: AsyncClient):
    """Registers a fresh user, creates one business, and returns everything
    a test typically needs: auth headers already scoped to that business,
    plus the raw ids for building test-specific assertions.
    """
    email = f"user-{uuid.uuid4().hex[:10]}@example.com"
    password = "password123"

    resp = await client.post(
        "/api/v1/auth/register",
        json={"name": "Test Owner", "email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["id"]

    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    onboarding_token = login.json()["access_token"]

    biz = await client.post(
        "/api/v1/businesses",
        json={"name": f"Store {uuid.uuid4().hex[:6]}", "currency": "INR"},
        headers={"Authorization": f"Bearer {onboarding_token}"},
    )
    assert biz.status_code == 201, biz.text
    business_id = biz.json()["id"]

    login2 = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    scoped_token = login2.json()["access_token"]
    assert login2.json()["selected_business_id"] == business_id

    return {
        "email": email,
        "password": password,
        "user_id": user_id,
        "business_id": business_id,
        "headers": {"Authorization": f"Bearer {scoped_token}"},
    }
