from httpx import AsyncClient


async def _create_product(client, headers, **overrides):
    payload = {"name": "Test Product", "stock_quantity": 20, "reorder_level": 5}
    payload.update(overrides)
    r = await client.post("/api/v1/products", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


class TestSaleWorkflow:
    async def test_unit_price_required(self, client: AsyncClient, registered_business):
        headers = registered_business["headers"]
        product = await _create_product(client, headers)
        r = await client.post(
            "/api/v1/transactions/sale",
            json={
                "items": [{"product_id": product["id"], "quantity": 2}],
                "payment_status": "PAID",
            },
            headers=headers,
        )
        assert r.status_code == 422

    async def test_valid_sale_deducts_stock_and_creates_transaction(
        self, client: AsyncClient, registered_business
    ):
        headers = registered_business["headers"]
        product = await _create_product(client, headers, stock_quantity=20)
        r = await client.post(
            "/api/v1/transactions/sale",
            json={
                "items": [{"product_id": product["id"], "quantity": 5, "unit_price": 100}],
                "payment_status": "PAID",
            },
            headers=headers,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["amount"] == "500.00" or float(body["amount"]) == 500
        assert len(body["items"]) == 1

        check = await client.get(f"/api/v1/products/{product['id']}", headers=headers)
        assert float(check.json()["stock_quantity"]) == 15

    async def test_multi_item_sale_rolls_back_entirely_on_insufficient_stock(
        self, client: AsyncClient, registered_business
    ):
        """The core atomicity guarantee: if ANY line item in a multi-product
        sale fails stock validation, NO product's stock should change."""
        headers = registered_business["headers"]
        p1 = await _create_product(client, headers, name="Plenty", stock_quantity=20)
        p2 = await _create_product(client, headers, name="Scarce", stock_quantity=2)

        r = await client.post(
            "/api/v1/transactions/sale",
            json={
                "items": [
                    {"product_id": p1["id"], "quantity": 5, "unit_price": 100},
                    {"product_id": p2["id"], "quantity": 50, "unit_price": 100},  # exceeds stock
                ],
                "payment_status": "PAID",
            },
            headers=headers,
        )
        assert r.status_code == 409

        # p1's stock must be untouched despite being valid on its own
        check1 = await client.get(f"/api/v1/products/{p1['id']}", headers=headers)
        assert float(check1.json()["stock_quantity"]) == 20

    async def test_sale_with_confirm_negative_stock_override(
        self, client: AsyncClient, registered_business
    ):
        headers = registered_business["headers"]
        product = await _create_product(client, headers, stock_quantity=3)
        r = await client.post(
            "/api/v1/transactions/sale",
            json={
                "items": [{"product_id": product["id"], "quantity": 10, "unit_price": 100}],
                "payment_status": "PAID",
                "confirm_negative_stock": True,
            },
            headers=headers,
        )
        assert r.status_code == 201
        check = await client.get(f"/api/v1/products/{product['id']}", headers=headers)
        assert float(check.json()["stock_quantity"]) == -7

    async def test_due_sale_updates_customer_balance(self, client: AsyncClient, registered_business):
        headers = registered_business["headers"]
        product = await _create_product(client, headers, stock_quantity=20)
        customer = await client.post(
            "/api/v1/customers", json={"name": "Ramesh", "phone": "9999999999"}, headers=headers
        )
        customer_id = customer.json()["id"]

        await client.post(
            "/api/v1/transactions/sale",
            json={
                "items": [{"product_id": product["id"], "quantity": 1, "unit_price": 100}],
                "payment_status": "DUE",
                "customer_id": customer_id,
            },
            headers=headers,
        )
        await client.post(
            "/api/v1/transactions/sale",
            json={
                "items": [{"product_id": product["id"], "quantity": 1, "unit_price": 50}],
                "payment_status": "DUE",
                "customer_id": customer_id,
            },
            headers=headers,
        )

        customers = await client.get("/api/v1/customers", headers=headers)
        matched = next(c for c in customers.json() if c["id"] == customer_id)
        assert float(matched["balance_due"]) == 150

    async def test_sale_for_nonexistent_product_returns_404(
        self, client: AsyncClient, registered_business
    ):
        r = await client.post(
            "/api/v1/transactions/sale",
            json={
                "items": [
                    {
                        "product_id": "00000000-0000-0000-0000-000000000000",
                        "quantity": 1,
                        "unit_price": 100,
                    }
                ],
                "payment_status": "PAID",
            },
            headers=registered_business["headers"],
        )
        assert r.status_code == 404


class TestExpenses:
    async def test_create_and_list_expense(self, client: AsyncClient, registered_business):
        headers = registered_business["headers"]
        r = await client.post(
            "/api/v1/expenses",
            json={"category": "rent", "amount": 5000, "note": "monthly rent"},
            headers=headers,
        )
        assert r.status_code == 201

        listing = await client.get("/api/v1/expenses", headers=headers)
        assert any(e["category"] == "rent" for e in listing.json())

    async def test_negative_expense_rejected(self, client: AsyncClient, registered_business):
        r = await client.post(
            "/api/v1/expenses",
            json={"category": "rent", "amount": -100},
            headers=registered_business["headers"],
        )
        assert r.status_code == 422


class TestFinanceTenantIsolation:
    async def test_transaction_not_visible_to_other_business(
        self, client: AsyncClient, registered_business
    ):
        headers = registered_business["headers"]
        product = await _create_product(client, headers)
        sale = await client.post(
            "/api/v1/transactions/sale",
            json={
                "items": [{"product_id": product["id"], "quantity": 1, "unit_price": 100}],
                "payment_status": "PAID",
            },
            headers=headers,
        )
        txn_id = sale.json()["id"]

        await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Other Owner",
                "email": "other-finance@example.com",
                "password": "password123",
            },
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "other-finance@example.com", "password": "password123"},
        )
        await client.post(
            "/api/v1/businesses",
            json={"name": "Other Shop 2", "currency": "INR"},
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        )
        login2 = await client.post(
            "/api/v1/auth/login",
            json={"email": "other-finance@example.com", "password": "password123"},
        )
        other_headers = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        r = await client.get(f"/api/v1/transactions/{txn_id}", headers=other_headers)
        assert r.status_code == 404
