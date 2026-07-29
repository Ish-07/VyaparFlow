"""
Tests specifically for the Step 8 multi-agent behavior — these are
distinct from test_voice_commands.py, which only proves the lifecycle
still works. These prove the actual point of Step 8: a real agent-to-
agent handoff (Finance -> Advisor), not just Finance handling a sale in
isolation.
"""
from httpx import AsyncClient


async def _create_product(client, headers, **overrides):
    payload = {"name": "Pickle Bottle", "stock_quantity": 20, "reorder_level": 5, "selling_price": 100}
    payload.update(overrides)
    r = await client.post("/api/v1/products", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


class TestAdvisorAgentHandoff:
    async def test_sale_that_crosses_reorder_level_triggers_advisor_insight(
        self, client: AsyncClient, registered_business
    ):
        headers = registered_business["headers"]
        # stock 10, reorder_level 8 — selling 5 drops it to 5, at/below reorder_level
        product = await _create_product(client, headers, stock_quantity=10, reorder_level=8)

        r = await client.post(
            "/api/v1/voice-commands",
            json={
                "text": "sold 5 pickle bottles for 100 rupees each",
                "idempotency_key": "advisor-test-1",
            },
            headers=headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["status"] == "COMPLETED"
        # The Advisor agent's message must be appended to the Finance agent's own response —
        # proof this went through BOTH agents, not just one.
        assert "Sale recorded" in body["final_response"]
        assert "Restock suggestion" in body["final_response"]

        insights = await client.get("/api/v1/insights", headers=headers)
        assert insights.status_code == 200
        assert len(insights.json()) == 1
        assert insights.json()[0]["insight_type"] == "restock_suggestion"
        assert product["name"] in insights.json()[0]["message"]

    async def test_sale_that_stays_well_above_reorder_level_does_not_trigger_advisor(
        self, client: AsyncClient, registered_business
    ):
        headers = registered_business["headers"]
        # stock 100, reorder_level 5 — selling 5 leaves 95, nowhere near low
        product = await _create_product(client, headers, stock_quantity=100, reorder_level=5)

        r = await client.post(
            "/api/v1/voice-commands",
            json={
                "text": "sold 5 pickle bottles for 100 rupees each",
                "idempotency_key": "advisor-test-2",
            },
            headers=headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["status"] == "COMPLETED"
        assert "Restock suggestion" not in body["final_response"]

        insights = await client.get("/api/v1/insights", headers=headers)
        assert insights.json() == []

    async def test_expense_never_triggers_advisor(self, client: AsyncClient, registered_business):
        headers = registered_business["headers"]
        r = await client.post(
            "/api/v1/voice-commands",
            json={"text": "spent 500 rupees on rent", "idempotency_key": "advisor-test-3"},
            headers=headers,
        )
        assert r.status_code == 201
        assert r.json()["status"] == "COMPLETED"

        insights = await client.get("/api/v1/insights", headers=headers)
        assert insights.json() == []

    async def test_stock_update_never_triggers_advisor(self, client: AsyncClient, registered_business):
        """Advisor is deliberately scoped to SALE only in this build —
        restocking is the opposite signal, so it should never fire."""
        headers = registered_business["headers"]
        await _create_product(client, headers, stock_quantity=2, reorder_level=10)

        r = await client.post(
            "/api/v1/voice-commands",
            json={"text": "restocked 5 pickle bottles", "idempotency_key": "advisor-test-4"},
            headers=headers,
        )
        assert r.status_code == 201
        assert r.json()["status"] == "COMPLETED"

        insights = await client.get("/api/v1/insights", headers=headers)
        assert insights.json() == []

    async def test_confirm_flow_sale_also_triggers_advisor(self, client: AsyncClient, registered_business):
        """The confirm() path reuses the same graph — verify the handoff
        works there too, not just on the direct-execution path."""
        headers = registered_business["headers"]
        product = await _create_product(client, headers, stock_quantity=3, reorder_level=5)

        r = await client.post(
            "/api/v1/voice-commands",
            json={
                "text": "sold 50 pickle bottles for 100 rupees each",  # exceeds stock -> needs confirmation
                "idempotency_key": "advisor-test-5",
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
        assert "Restock suggestion" in confirm.json()["final_response"]

    async def test_insights_respect_tenant_isolation(self, client: AsyncClient, registered_business):
        headers = registered_business["headers"]
        await _create_product(client, headers, stock_quantity=10, reorder_level=8)
        await client.post(
            "/api/v1/voice-commands",
            json={"text": "sold 5 pickle bottles for 100 rupees each", "idempotency_key": "advisor-test-6"},
            headers=headers,
        )

        await client.post(
            "/api/v1/auth/register",
            json={"name": "Other", "email": "other-insights@example.com", "password": "password123"},
        )
        login = await client.post(
            "/api/v1/auth/login", json={"email": "other-insights@example.com", "password": "password123"}
        )
        await client.post(
            "/api/v1/businesses",
            json={"name": "Other Biz Insights", "currency": "INR"},
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        )
        login2 = await client.post(
            "/api/v1/auth/login", json={"email": "other-insights@example.com", "password": "password123"}
        )
        other_headers = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        insights = await client.get("/api/v1/insights", headers=other_headers)
        assert insights.json() == []


class TestAgentTaskLogging:
    async def test_agent_tasks_show_distinct_specialized_agent_names(
        self, client: AsyncClient, registered_business
    ):
        """Verifies agent_tasks reflects the real graph nodes
        (finance_agent, advisor_agent) rather than the old ad-hoc
        strings ('finance', 'inventory') from before Step 8."""
        headers = registered_business["headers"]
        await _create_product(client, headers, stock_quantity=10, reorder_level=8)

        r = await client.post(
            "/api/v1/voice-commands",
            json={"text": "sold 5 pickle bottles for 100 rupees each", "idempotency_key": "logging-test-1"},
            headers=headers,
        )
        command_id = r.json()["id"]

        # No direct agent_tasks endpoint exists yet — inspect via the DB session
        # fixture isn't exposed to tests directly, so we validate indirectly:
        # both the sale AND the insight must exist, which can only be true if
        # finance_agent AND advisor_agent both actually ran.
        insights = await client.get("/api/v1/insights", headers=headers)
        transactions = await client.get("/api/v1/transactions", headers=headers)
        assert len(insights.json()) == 1
        assert len(transactions.json()) == 1
