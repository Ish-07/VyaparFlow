import uuid

import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str, password: str = "password123"):
    r = await client.post(
        "/api/v1/auth/register", json={"name": "Tester", "email": email, "password": password}
    )
    assert r.status_code == 201, r.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()


class TestRegisterAndLogin:
    async def test_register_creates_user(self, client: AsyncClient):
        email = f"reg-{uuid.uuid4().hex[:8]}@example.com"
        r = await client.post(
            "/api/v1/auth/register",
            json={"name": "Alice", "email": email, "password": "password123"},
        )
        assert r.status_code == 201
        assert r.json()["email"] == email

    async def test_duplicate_email_rejected(self, client: AsyncClient):
        email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={"name": "Alice", "email": email, "password": "password123"},
        )
        r = await client.post(
            "/api/v1/auth/register",
            json={"name": "Alice2", "email": email, "password": "password123"},
        )
        assert r.status_code == 409

    async def test_wrong_password_rejected(self, client: AsyncClient):
        email = f"wp-{uuid.uuid4().hex[:8]}@example.com"
        await _register_and_login(client, email)
        r = await client.post(
            "/api/v1/auth/login", json={"email": email, "password": "wrong-password"}
        )
        assert r.status_code == 401

    async def test_login_unknown_email_rejected(self, client: AsyncClient):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "whatever123"},
        )
        assert r.status_code == 401


class TestBusinessSelection:
    async def test_zero_businesses_needs_onboarding(self, client: AsyncClient):
        email = f"zero-{uuid.uuid4().hex[:8]}@example.com"
        login = await _register_and_login(client, email)
        assert login["needs_onboarding"] is True
        assert login["selected_business_id"] is None
        assert login["businesses"] == []

    async def test_me_unscoped_has_null_business(self, client: AsyncClient):
        email = f"unscoped-{uuid.uuid4().hex[:8]}@example.com"
        login = await _register_and_login(client, email)
        r = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {login['access_token']}"}
        )
        assert r.status_code == 200
        assert r.json()["business_id"] is None

    async def test_one_business_auto_selected_on_login(self, client: AsyncClient):
        email = f"one-{uuid.uuid4().hex[:8]}@example.com"
        login = await _register_and_login(client, email)
        biz = await client.post(
            "/api/v1/businesses",
            json={"name": "Solo Shop", "currency": "INR"},
            headers={"Authorization": f"Bearer {login['access_token']}"},
        )
        business_id = biz.json()["id"]

        login2 = await client.post(
            "/api/v1/auth/login", json={"email": email, "password": "password123"}
        )
        body = login2.json()
        assert body["selected_business_id"] == business_id
        assert body["needs_onboarding"] is False

        me = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
        )
        assert me.json()["business_id"] == business_id
        assert me.json()["role"] == "owner"

    async def test_multiple_businesses_not_auto_selected(self, client: AsyncClient):
        email = f"multi-{uuid.uuid4().hex[:8]}@example.com"
        login = await _register_and_login(client, email)
        headers = {"Authorization": f"Bearer {login['access_token']}"}

        b1 = await client.post(
            "/api/v1/businesses", json={"name": "Shop A", "currency": "INR"}, headers=headers
        )
        b2 = await client.post(
            "/api/v1/businesses", json={"name": "Shop B", "currency": "INR"}, headers=headers
        )
        b1_id, b2_id = b1.json()["id"], b2.json()["id"]

        login2 = await client.post(
            "/api/v1/auth/login", json={"email": email, "password": "password123"}
        )
        body = login2.json()
        assert body["selected_business_id"] is None
        assert {b["business_id"] for b in body["businesses"]} == {b1_id, b2_id}

        # Unscoped token must be rejected by any business-scoped endpoint
        unscoped_headers = {"Authorization": f"Bearer {body['access_token']}"}
        r = await client.get("/api/v1/products", headers=unscoped_headers)
        assert r.status_code == 400

        # Selecting one business scopes the token correctly
        select = await client.post(
            "/api/v1/auth/select-business",
            json={"business_id": b1_id},
            headers=unscoped_headers,
        )
        assert select.status_code == 200
        assert select.json()["selected_business_id"] == b1_id

    async def test_select_business_rejects_non_member(self, client: AsyncClient):
        """A user cannot select a business they don't belong to."""
        email_a = f"a-{uuid.uuid4().hex[:8]}@example.com"
        email_b = f"b-{uuid.uuid4().hex[:8]}@example.com"
        login_a = await _register_and_login(client, email_a)
        login_b = await _register_and_login(client, email_b)

        biz_a = await client.post(
            "/api/v1/businesses",
            json={"name": "A's Shop", "currency": "INR"},
            headers={"Authorization": f"Bearer {login_a['access_token']}"},
        )
        biz_a_id = biz_a.json()["id"]

        r = await client.post(
            "/api/v1/auth/select-business",
            json={"business_id": biz_a_id},
            headers={"Authorization": f"Bearer {login_b['access_token']}"},
        )
        assert r.status_code == 403
