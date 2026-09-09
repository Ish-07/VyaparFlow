"""
Voice command lifecycle tests, covering both the rule-based fallback path
(the default in tests, since no LLM_API_KEY is configured) and a mocked
LLM path — proving AIRouter integration didn't change the safety
guarantees (tenant isolation, stock policy, confirmation flow) that
existed before Step 7.
"""
import json
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient

from app.services.ai.base import ParsedCommand
from app.services.ai.providers.gemini_provider import GeminiProvider


async def _create_product(client, headers, **overrides):
    payload = {"name": "Pickle Bottle", "stock_quantity": 20, "reorder_level": 5, "selling_price": 100}
    payload.update(overrides)
    r = await client.post("/api/v1/products", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


class TestVoiceCommandRuleBasedPath:
    """No LLM_API_KEY is set in the test environment (see conftest.py),
    so these exercise the rule-based fallback — proving the lifecycle
    itself works regardless of which provider answers."""

    async def test_sale_command_completes_and_deducts_stock(
        self, client: AsyncClient, registered_business
    ):
        headers = registered_business["headers"]
        product = await _create_product(client, headers)

        r = await client.post(
            "/api/v1/voice-commands",
            json={
                "text": "sold 5 pickle bottles for 100 rupees each",
                "idempotency_key": "vc-test-1",
            },
            headers=headers,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["status"] == "COMPLETED"
        assert body["intent"] == "SALE"

        check = await client.get(f"/api/v1/products/{product['id']}", headers=headers)
        assert float(check.json()["stock_quantity"]) == 15

    async def test_idempotency_key_prevents_double_execution(
        self, client: AsyncClient, registered_business
    ):
        headers = registered_business["headers"]
        product = await _create_product(client, headers)

        payload = {
            "text": "sold 5 pickle bottles for 100 rupees each",
            "idempotency_key": "vc-test-dup",
        }
        r1 = await client.post("/api/v1/voice-commands", json=payload, headers=headers)
        r2 = await client.post("/api/v1/voice-commands", json=payload, headers=headers)
        assert r1.json()["id"] == r2.json()["id"]

        check = await client.get(f"/api/v1/products/{product['id']}", headers=headers)
        assert float(check.json()["stock_quantity"]) == 15  # only deducted ONCE

    async def test_unknown_command_needs_confirmation(
        self, client: AsyncClient, registered_business
    ):
        r = await client.post(
            "/api/v1/voice-commands",
            json={"text": "asdkj nonsense gibberish", "idempotency_key": "vc-test-unknown"},
            headers=registered_business["headers"],
        )
        assert r.status_code == 201
        assert r.json()["status"] == "NEEDS_CONFIRMATION"

    async def test_insufficient_stock_needs_confirmation_then_confirm_completes(
        self, client: AsyncClient, registered_business
    ):
        headers = registered_business["headers"]
        product = await _create_product(client, headers, stock_quantity=2)

        r = await client.post(
            "/api/v1/voice-commands",
            json={
                "text": "sold 50 pickle bottles for 100 rupees each",
                "idempotency_key": "vc-test-negstock",
            },
            headers=headers,
        )
        assert r.json()["status"] == "NEEDS_CONFIRMATION"
        command_id = r.json()["id"]

        confirm = await client.post(
            f"/api/v1/voice-commands/{command_id}/confirm",
            json={"product_id": product["id"], "confirm_negative_stock": True},
            headers=headers,
        )
        assert confirm.status_code == 200
        assert confirm.json()["status"] == "COMPLETED"

    async def test_product_not_found_needs_confirmation_then_confirm_with_explicit_id(
        self, client: AsyncClient, registered_business
    ):
        headers = registered_business["headers"]
        product = await _create_product(client, headers, name="Jam Jar")

        r = await client.post(
            "/api/v1/voice-commands",
            json={
                "text": "sold 2 nonexistent widgets for 50 rupees each",
                "idempotency_key": "vc-test-noprod",
            },
            headers=headers,
        )
        assert r.json()["status"] == "NEEDS_CONFIRMATION"
        command_id = r.json()["id"]

        confirm = await client.post(
            f"/api/v1/voice-commands/{command_id}/confirm",
            json={"product_id": product["id"], "quantity": 2, "unit_price": 50},
            headers=headers,
        )
        assert confirm.status_code == 200
        assert confirm.json()["status"] == "COMPLETED"

    async def test_confirming_completed_command_rejected(
        self, client: AsyncClient, registered_business
    ):
        headers = registered_business["headers"]
        product = await _create_product(client, headers)
        r = await client.post(
            "/api/v1/voice-commands",
            json={
                "text": "sold 1 pickle bottles for 100 rupees each",
                "idempotency_key": "vc-test-doubleconfirm",
            },
            headers=headers,
        )
        command_id = r.json()["id"]
        assert r.json()["status"] == "COMPLETED"

        confirm = await client.post(
            f"/api/v1/voice-commands/{command_id}/confirm",
            json={"product_id": product["id"]},
            headers=headers,
        )
        assert confirm.status_code == 409

    async def test_tenant_isolation_command_not_visible_to_other_business(
        self, client: AsyncClient, registered_business
    ):
        headers = registered_business["headers"]
        await _create_product(client, headers)
        r = await client.post(
            "/api/v1/voice-commands",
            json={
                "text": "sold 1 pickle bottles for 100 rupees each",
                "idempotency_key": "vc-test-isolation",
            },
            headers=headers,
        )
        command_id = r.json()["id"]

        await client.post(
            "/api/v1/auth/register",
            json={"name": "Other", "email": "other-vc@example.com", "password": "password123"},
        )
        login = await client.post(
            "/api/v1/auth/login", json={"email": "other-vc@example.com", "password": "password123"}
        )
        await client.post(
            "/api/v1/businesses",
            json={"name": "Other Biz", "currency": "INR"},
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        )
        login2 = await client.post(
            "/api/v1/auth/login", json={"email": "other-vc@example.com", "password": "password123"}
        )
        other_headers = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        r2 = await client.get(f"/api/v1/voice-commands/{command_id}", headers=other_headers)
        assert r2.status_code == 404


class TestVoiceCommandWithMockedLLM:
    """Proves the LLM path itself (not just the fallback) drives the same
    lifecycle correctly, using a mocked Geminiresponse — no real API
    key or network call needed.
    """

    async def test_llm_parsed_sale_executes_through_full_lifecycle(
        self, client: AsyncClient, registered_business, monkeypatch
    ):
        headers = registered_business["headers"]
        product = await _create_product(client, headers)

        async def fake_parse_command(self, text, business_context):
            return ParsedCommand(
                intent="SALE",
                confidence=0.97,
                entities={"product_name": "Pickle Bottle", "quantity": 3, "unit_price": 100},
                provider_used="gemini",
                model_used="gemini-3.6-flash",
                latency_ms=250.0,
            )

        monkeypatch.setattr(GeminiProvider, "parse_command", fake_parse_command)

        from app.services.ai.router import AIRouter
        import app.api.v1.endpoints.voice_commands as vc_endpoint_module

        original_service = vc_endpoint_module.VoiceCommandService

        def patched_service(session):
            svc = original_service(session)
            svc.ai_router = AIRouter(
                primary=GeminiProvider(
    api_key="fake",
    base_url="https://fake/v1",
    model="fake-model",
    timeout_seconds=5,
    embedding_model="gemini-embedding-001",
    embedding_dimension=1536,
)
            )
            return svc

        monkeypatch.setattr(vc_endpoint_module, "VoiceCommandService", patched_service)

        r = await client.post(
            "/api/v1/voice-commands",
            json={
                "text": "sold 3 pickle bottles for 100 rupees each",
                "idempotency_key": "vc-test-llm-mocked",
            },
            headers=headers,
        )
        assert r.status_code == 201, r.text
        assert r.json()["status"] == "COMPLETED"

        check = await client.get(f"/api/v1/products/{product['id']}", headers=headers)
        assert float(check.json()["stock_quantity"]) == 17  # 20 - 3
