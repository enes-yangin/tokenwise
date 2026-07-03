def mk_product(client, **over):
    body = {
        "name": "Widget",
        "sku": "SKU-1",
        "price_cents": 100,
        "stock": 10,
        "category": "tools",
    }
    body.update(over)
    return client.post("/products", json=body)


# ---------- Products ----------
def test_create_product_201(client):
    r = mk_product(client)
    assert r.status_code == 201
    d = r.json()
    assert d["id"] >= 1
    assert d["sku"] == "SKU-1"
    assert d["stock"] == 10


def test_create_duplicate_sku_409(client):
    mk_product(client)
    r = mk_product(client, name="Other")
    assert r.status_code == 409


def test_create_negative_price_422(client):
    assert mk_product(client, price_cents=-1).status_code == 422


def test_create_negative_stock_422(client):
    assert mk_product(client, stock=-1).status_code == 422


def test_create_missing_field_422(client):
    assert client.post("/products", json={"name": "x"}).status_code == 422


def test_get_product_404(client):
    assert client.get("/products/999").status_code == 404


def test_list_filter_and_pagination(client):
    mk_product(client, sku="a", category="x")
    mk_product(client, sku="b", category="y")
    mk_product(client, sku="c", category="x")
    r = client.get("/products", params={"category": "x"})
    assert r.status_code == 200
    assert {p["sku"] for p in r.json()} == {"a", "c"}
    # pagination
    r2 = client.get("/products", params={"limit": 1, "offset": 1})
    assert len(r2.json()) == 1
    # offset beyond end -> empty, not error
    r3 = client.get("/products", params={"offset": 999})
    assert r3.status_code == 200
    assert r3.json() == []


def test_patch_product(client):
    pid = mk_product(client).json()["id"]
    r = client.patch(f"/products/{pid}", json={"price_cents": 200})
    assert r.status_code == 200
    assert r.json()["price_cents"] == 200
    assert client.patch("/products/999", json={"price_cents": 1}).status_code == 404


def test_delete_product(client):
    pid = mk_product(client).json()["id"]
    assert client.delete(f"/products/{pid}").status_code == 204
    assert client.delete(f"/products/{pid}").status_code == 404


def test_delete_referenced_product_409(client):
    pid = mk_product(client, stock=5).json()["id"]
    client.post("/orders", json={"items": [{"product_id": pid, "quantity": 1}]})
    assert client.delete(f"/products/{pid}").status_code == 409


# ---------- Orders ----------
def test_create_order_snapshot_and_stock(client):
    pid = mk_product(client, price_cents=100, stock=10).json()["id"]
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 3}]})
    assert r.status_code == 201
    d = r.json()
    assert d["status"] == "pending"
    assert d["total_cents"] == 300
    assert "created_at" in d
    assert client.get(f"/products/{pid}").json()["stock"] == 7


def test_order_missing_product_404(client):
    assert client.post("/orders", json={"items": [{"product_id": 999, "quantity": 1}]}).status_code == 404


def test_order_empty_items_422(client):
    assert client.post("/orders", json={"items": []}).status_code == 422


def test_order_bad_quantity_422(client):
    pid = mk_product(client).json()["id"]
    assert client.post("/orders", json={"items": [{"product_id": pid, "quantity": 0}]}).status_code == 422


def test_atomic_insufficient_stock_no_partial(client):
    a = mk_product(client, sku="a", stock=5).json()["id"]
    b = mk_product(client, sku="b", stock=1).json()["id"]
    r = client.post("/orders", json={"items": [
        {"product_id": a, "quantity": 2},
        {"product_id": b, "quantity": 5},
    ]})
    assert r.status_code == 409
    assert client.get(f"/products/{a}").json()["stock"] == 5
    assert client.get(f"/products/{b}").json()["stock"] == 1


def test_price_snapshot_unaffected_by_patch(client):
    pid = mk_product(client, price_cents=100, stock=10).json()["id"]
    oid = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 2}]}).json()["id"]
    client.patch(f"/products/{pid}", json={"price_cents": 999})
    assert client.get(f"/orders/{oid}").json()["total_cents"] == 200


def test_get_order_404(client):
    assert client.get("/orders/999").status_code == 404


def test_cancel_restocks(client):
    pid = mk_product(client, stock=10).json()["id"]
    oid = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 4}]}).json()["id"]
    assert client.get(f"/products/{pid}").json()["stock"] == 6
    r = client.post(f"/orders/{oid}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    assert client.get(f"/products/{pid}").json()["stock"] == 10


def test_cancel_idempotency(client):
    pid = mk_product(client, stock=10).json()["id"]
    oid = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 4}]}).json()["id"]
    assert client.post(f"/orders/{oid}/cancel").status_code == 200
    assert client.post(f"/orders/{oid}/cancel").status_code == 409
    assert client.get(f"/products/{pid}").json()["stock"] == 10  # not double-restocked


def test_cancel_404(client):
    assert client.post("/orders/999/cancel").status_code == 404


# ---------- Reports ----------
def test_low_stock(client):
    mk_product(client, sku="a", stock=5)
    mk_product(client, sku="b", stock=50)
    r = client.get("/reports/low-stock", params={"threshold": 10})
    assert {p["sku"] for p in r.json()} == {"a"}
    # default threshold = 10
    assert {p["sku"] for p in client.get("/reports/low-stock").json()} == {"a"}


def test_revenue_by_category_excludes_cancelled(client):
    a = mk_product(client, sku="a", price_cents=100, stock=10, category="tools").json()["id"]
    b = mk_product(client, sku="b", price_cents=200, stock=10, category="food").json()["id"]
    client.post("/orders", json={"items": [{"product_id": a, "quantity": 2}]})  # 200 tools
    o2 = client.post("/orders", json={"items": [{"product_id": b, "quantity": 1}]}).json()["id"]  # 200 food
    client.post(f"/orders/{o2}/cancel")
    rev = client.get("/reports/revenue-by-category").json()
    assert rev.get("tools") == 200
    assert "food" not in rev or rev.get("food") == 0
