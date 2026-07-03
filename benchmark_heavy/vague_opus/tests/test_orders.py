"""Order endpoint testleri."""


def _make_product(client, sku, price=500, stock=10, category="tools"):
    r = client.post("/products", json={
        "name": "P", "sku": sku, "price_cents": price,
        "stock": stock, "category": category})
    assert r.status_code == 201
    return r.json()["id"]


def test_create_order_response_shape(client):
    pid = _make_product(client, "O1", price=300, stock=5)
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 2}]})
    assert r.status_code == 201
    body = r.json()
    assert set(body) == {"id", "status", "created_at", "items", "total_cents"}
    assert body["status"] == "created"
    assert body["total_cents"] == 600
    item = body["items"][0]
    assert item == {"product_id": pid, "quantity": 2, "unit_price_cents": 300}


def test_create_order_decrements_stock(client):
    pid = _make_product(client, "O2", stock=10)
    client.post("/orders", json={"items": [{"product_id": pid, "quantity": 3}]})
    assert client.get(f"/products/{pid}").json()["stock"] == 7


def test_get_order(client):
    pid = _make_product(client, "O3")
    oid = client.post(
        "/orders", json={"items": [{"product_id": pid, "quantity": 1}]}
    ).json()["id"]
    r = client.get(f"/orders/{oid}")
    assert r.status_code == 200
    assert r.json()["id"] == oid


def test_get_order_404(client):
    assert client.get("/orders/999").status_code == 404


def test_create_order_unknown_product_404(client):
    r = client.post("/orders", json={"items": [{"product_id": 999, "quantity": 1}]})
    assert r.status_code == 404


def test_create_order_insufficient_stock_409(client):
    pid = _make_product(client, "O4", stock=2)
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 5}]})
    assert r.status_code == 409
    # stok değişmemeli
    assert client.get(f"/products/{pid}").json()["stock"] == 2


def test_empty_items_422(client):
    assert client.post("/orders", json={"items": []}).status_code == 422


def test_zero_quantity_422(client):
    pid = _make_product(client, "O5")
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 0}]})
    assert r.status_code == 422


def test_cancel_restocks(client):
    pid = _make_product(client, "O6", stock=10)
    oid = client.post(
        "/orders", json={"items": [{"product_id": pid, "quantity": 4}]}
    ).json()["id"]
    assert client.get(f"/products/{pid}").json()["stock"] == 6
    r = client.post(f"/orders/{oid}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    assert client.get(f"/products/{pid}").json()["stock"] == 10


def test_double_cancel_409(client):
    pid = _make_product(client, "O7")
    oid = client.post(
        "/orders", json={"items": [{"product_id": pid, "quantity": 1}]}
    ).json()["id"]
    assert client.post(f"/orders/{oid}/cancel").status_code == 200
    assert client.post(f"/orders/{oid}/cancel").status_code == 409


def test_cancel_404(client):
    assert client.post("/orders/999/cancel").status_code == 404


def test_duplicate_product_lines_merge(client):
    pid = _make_product(client, "O8", price=100, stock=10)
    r = client.post("/orders", json={"items": [
        {"product_id": pid, "quantity": 2},
        {"product_id": pid, "quantity": 3},
    ]})
    assert r.status_code == 201
    assert r.json()["total_cents"] == 500
    assert client.get(f"/products/{pid}").json()["stock"] == 5


def test_revenue_by_category(client):
    tools = _make_product(client, "RT", price=200, stock=10, category="tools")
    food = _make_product(client, "RF", price=150, stock=10, category="food")
    client.post("/orders", json={"items": [{"product_id": tools, "quantity": 2}]})
    client.post("/orders", json={"items": [{"product_id": food, "quantity": 3}]})
    report = client.get("/reports/revenue-by-category").json()
    assert report == {"tools": 400, "food": 450}


def test_cancelled_orders_excluded_from_revenue(client):
    pid = _make_product(client, "RC", price=100, stock=10, category="x")
    oid = client.post(
        "/orders", json={"items": [{"product_id": pid, "quantity": 2}]}
    ).json()["id"]
    client.post(f"/orders/{oid}/cancel")
    assert client.get("/reports/revenue-by-category").json() == {}
