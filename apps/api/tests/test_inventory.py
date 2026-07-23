from httpx import AsyncClient


async def _create_product(client, headers, **overrides):
    payload = {
        "name": "Pickle Bottle",
        "unit": "bottle",
        "cost_price": 50,
        "selling_price": 100,
        "stock_quantity": 20,
        "reorder_level": 5,
    }
    payload.update(overrides)
    r = await client.post("/api/v1/products", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


class TestProductCreation:
    async def test_create_product(self, client: AsyncClient, registered_business):
        product = await _create_product(client, registered_business["headers"])
        assert product["stock_quantity"] == "20.00" or float(product["stock_quantity"]) == 20
        assert product["is_low_stock"] is False

    async def test_duplicate_name_rejected(self, client: AsyncClient, registered_business):
        headers = registered_business["headers"]
        await _create_product(client, headers, name="Unique Item")
        r = await client.post(
            "/api/v1/products",
            json={"name": "Unique Item", "stock_quantity": 5},
            headers=headers,
        )
        assert r.status_code == 409

    async def test_negative_price_rejected(self, client: AsyncClient, registered_business):
        r = await client.post(
            "/api/v1/products",
            json={"name": "Bad Product", "cost_price": -10},
            headers=registered_business["headers"],
        )
        assert r.status_code == 422


class TestStockAdjustment:
    async def test_normal_deduct(self, client: AsyncClient, registered_business):
        headers = registered_business["headers"]
        product = await _create_product(client, headers)
        r = await client.patch(
            f"/api/v1/products/{product['id']}/stock",
            json={"quantity_change": -5, "reference_type": "sale"},
            headers=headers,
        )
        assert r.status_code == 200
        assert float(r.json()["product"]["stock_quantity"]) == 15

    async def test_deduct_more_than_available_blocked(self, client: AsyncClient, registered_business):
        headers = registered_business["headers"]
        product = await _create_product(client, headers, stock_quantity=10)
        r = await client.patch(
            f"/api/v1/products/{product['id']}/stock",
            json={"quantity_change": -100, "reference_type": "sale"},
            headers=headers,
        )
        assert r.status_code == 409

        # stock must be UNCHANGED after a blocked attempt
        check = await client.get(f"/api/v1/products/{product['id']}", headers=headers)
        assert float(check.json()["stock_quantity"]) == 10

    async def test_deduct_more_than_available_with_override_succeeds(
        self, client: AsyncClient, registered_business
    ):
        headers = registered_business["headers"]
        product = await _create_product(client, headers, stock_quantity=10)
        r = await client.patch(
            f"/api/v1/products/{product['id']}/stock",
            json={
                "quantity_change": -100,
                "reference_type": "sale",
                "confirm_negative_stock": True,
            },
            headers=headers,
        )
        assert r.status_code == 200
        assert float(r.json()["product"]["stock_quantity"]) == -90

    async def test_low_stock_flag_and_filter(self, client: AsyncClient, registered_business):
        headers = registered_business["headers"]
        product = await _create_product(client, headers, stock_quantity=10, reorder_level=5)

        await client.patch(
            f"/api/v1/products/{product['id']}/stock",
            json={"quantity_change": -6, "reference_type": "sale"},
            headers=headers,
        )

        check = await client.get(f"/api/v1/products/{product['id']}", headers=headers)
        assert check.json()["is_low_stock"] is True

        low_stock = await client.get("/api/v1/products?low_stock_only=true", headers=headers)
        assert any(p["id"] == product["id"] for p in low_stock.json())


class TestTenantIsolation:
    async def test_product_not_visible_to_other_business(
        self, client: AsyncClient, registered_business
    ):
        product = await _create_product(client, registered_business["headers"])

        # A second, unrelated business/user
        r = await client.post(
            "/api/v1/auth/register",
            json={"name": "Other Owner", "email": "other-tenant@example.com", "password": "password123"},
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "other-tenant@example.com", "password": "password123"},
        )
        onboarding_token = login.json()["access_token"]
        await client.post(
            "/api/v1/businesses",
            json={"name": "Other Shop", "currency": "INR"},
            headers={"Authorization": f"Bearer {onboarding_token}"},
        )
        login2 = await client.post(
            "/api/v1/auth/login",
            json={"email": "other-tenant@example.com", "password": "password123"},
        )
        other_headers = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        r = await client.get(f"/api/v1/products/{product['id']}", headers=other_headers)
        assert r.status_code == 404

        r2 = await client.patch(
            f"/api/v1/products/{product['id']}/stock",
            json={"quantity_change": -1},
            headers=other_headers,
        )
        assert r2.status_code == 404
