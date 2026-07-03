"""Order endpoint testleri."""


def _make_product(client, sku, price_cents, stock, category="tools"):
    r = client.post("/products", json={
        "name": f"Product {sku}", "sku": sku, "price_cents": price_cents,
        "stock": stock, "category": category})
    assert r.status_code == 201
    return r.json()["id"]


def test_create_order_and_get(client):
    pid = _make_product(client, "O1", 500, 10)
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 2}]})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "created"
    assert body["total_cents"] == 1000
    assert body["items"] == [
        {"product_id": pid, "quantity": 2, "unit_price_cents": 500}
    ]
    assert "created_at" in body

    order_id = body["id"]
    got = client.get(f"/orders/{order_id}")
    assert got.status_code == 200
    assert got.json() == body


def test_create_order_reduces_stock(client):
    pid = _make_product(client, "O2", 100, 5)
    client.post("/orders", json={"items": [{"product_id": pid, "quantity": 3}]})
    assert client.get(f"/products/{pid}").json()["stock"] == 2


def test_create_order_multiple_items(client):
    p1 = _make_product(client, "O3", 100, 5)
    p2 = _make_product(client, "O4", 200, 5)
    r = client.post("/orders", json={
        "items": [
            {"product_id": p1, "quantity": 2},
            {"product_id": p2, "quantity": 1},
        ]
    })
    assert r.status_code == 201
    assert r.json()["total_cents"] == 2 * 100 + 1 * 200


def test_create_order_unknown_product_404(client):
    r = client.post("/orders", json={"items": [{"product_id": 9999, "quantity": 1}]})
    assert r.status_code == 404


def test_create_order_insufficient_stock_409(client):
    pid = _make_product(client, "O5", 100, 1)
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 5}]})
    assert r.status_code == 409


def test_get_order_not_found_404(client):
    assert client.get("/orders/9999").status_code == 404


def test_cancel_order_restores_stock(client):
    pid = _make_product(client, "O6", 100, 5)
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 3}]})
    order_id = r.json()["id"]
    assert client.get(f"/products/{pid}").json()["stock"] == 2

    cancel = client.post(f"/orders/{order_id}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"
    assert client.get(f"/products/{pid}").json()["stock"] == 5


def test_cancel_order_twice_409(client):
    pid = _make_product(client, "O7", 100, 5)
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 1}]})
    order_id = r.json()["id"]
    assert client.post(f"/orders/{order_id}/cancel").status_code == 200
    assert client.post(f"/orders/{order_id}/cancel").status_code == 409


def test_cancel_order_not_found_404(client):
    assert client.post("/orders/9999/cancel").status_code == 404


def test_create_order_empty_items_422(client):
    r = client.post("/orders", json={"items": []})
    assert r.status_code == 422


def test_create_order_zero_quantity_422(client):
    pid = _make_product(client, "O8", 100, 5)
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 0}]})
    assert r.status_code == 422


def test_revenue_by_category(client):
    p1 = _make_product(client, "R1", 1000, 10, category="cat-a")
    p2 = _make_product(client, "R2", 500, 10, category="cat-b")

    client.post("/orders", json={"items": [{"product_id": p1, "quantity": 2}]})
    client.post("/orders", json={"items": [{"product_id": p2, "quantity": 3}]})

    report = client.get("/reports/revenue-by-category")
    assert report.status_code == 200
    data = report.json()
    assert data["cat-a"] == 2000
    assert data["cat-b"] == 1500


def test_revenue_excludes_cancelled_orders(client):
    pid = _make_product(client, "R3", 1000, 10, category="cat-c")
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 2}]})
    order_id = r.json()["id"]
    client.post(f"/orders/{order_id}/cancel")

    report = client.get("/reports/revenue-by-category")
    assert report.json().get("cat-c") is None
