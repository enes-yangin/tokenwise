"""Order endpoint testleri."""


def _make_product(client, sku, price_cents, stock, category="tools"):
    r = client.post("/products", json={
        "name": sku, "sku": sku, "price_cents": price_cents,
        "stock": stock, "category": category})
    return r.json()["id"]


def test_create_order_success_and_stock_decrement(client):
    pid = _make_product(client, "O1", 500, 10)
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 3}]})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "created"
    assert body["total_cents"] == 1500
    assert body["items"] == [{"product_id": pid, "quantity": 3, "unit_price_cents": 500}]
    assert "created_at" in body and "id" in body

    assert client.get(f"/products/{pid}").json()["stock"] == 7


def test_get_order_shape_and_404(client):
    pid = _make_product(client, "O2", 200, 5)
    oid = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 2}]}).json()["id"]
    r = client.get(f"/orders/{oid}")
    assert r.status_code == 200
    assert r.json()["id"] == oid

    assert client.get("/orders/999999").status_code == 404


def test_create_order_unknown_product_404(client):
    r = client.post("/orders", json={"items": [{"product_id": 999999, "quantity": 1}]})
    assert r.status_code == 404


def test_create_order_insufficient_stock_409(client):
    pid = _make_product(client, "O3", 100, 2)
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 5}]})
    assert r.status_code == 409


def test_cancel_order_restocks(client):
    pid = _make_product(client, "O4", 300, 10)
    oid = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 4}]}).json()["id"]
    assert client.get(f"/products/{pid}").json()["stock"] == 6

    r = client.post(f"/orders/{oid}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    assert client.get(f"/products/{pid}").json()["stock"] == 10


def test_cancel_already_cancelled_409(client):
    pid = _make_product(client, "O5", 100, 10)
    oid = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 1}]}).json()["id"]
    client.post(f"/orders/{oid}/cancel")
    assert client.post(f"/orders/{oid}/cancel").status_code == 409


def test_revenue_by_category(client):
    p1 = _make_product(client, "R1", 1000, 10, category="cat-a")
    p2 = _make_product(client, "R2", 500, 10, category="cat-b")
    client.post("/orders", json={"items": [{"product_id": p1, "quantity": 2}]})
    client.post("/orders", json={"items": [{"product_id": p2, "quantity": 3}]})

    r = client.get("/reports/revenue-by-category")
    assert r.status_code == 200
    body = r.json()
    assert body["cat-a"] == 2000
    assert body["cat-b"] == 1500


def test_cancelled_order_excluded_from_revenue(client):
    pid = _make_product(client, "R3", 100, 10, category="cat-c")
    oid = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 1}]}).json()["id"]
    client.post(f"/orders/{oid}/cancel")

    r = client.get("/reports/revenue-by-category")
    assert r.json().get("cat-c") is None
