"""Order endpoint testleri."""


def _mk_product(client, sku="W1", price=500, stock=10, category="tools"):
    r = client.post("/products", json={
        "name": "Widget", "sku": sku, "price_cents": price,
        "stock": stock, "category": category})
    assert r.status_code == 201
    return r.json()["id"]


def test_create_and_get_order(client):
    pid = _mk_product(client, sku="A", price=500, stock=10)
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 3}]})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    assert body["total_cents"] == 1500
    assert body["items"][0]["unit_price_cents"] == 500
    assert "created_at" in body
    oid = body["id"]
    assert client.get(f"/orders/{oid}").json()["total_cents"] == 1500
    # stok düştü
    assert client.get(f"/products/{pid}").json()["stock"] == 7


def test_insufficient_stock_atomic_no_partial(client):
    p1 = _mk_product(client, sku="P1", stock=5)
    p2 = _mk_product(client, sku="P2", stock=1)
    r = client.post("/orders", json={"items": [
        {"product_id": p1, "quantity": 2},
        {"product_id": p2, "quantity": 5},
    ]})
    assert r.status_code == 409
    # kısmi düşüm olmamalı
    assert client.get(f"/products/{p1}").json()["stock"] == 5
    assert client.get(f"/products/{p2}").json()["stock"] == 1


def test_same_product_multiple_lines_aggregated(client):
    pid = _mk_product(client, sku="AGG", stock=5)
    # toplam 6 > 5 → 409
    r = client.post("/orders", json={"items": [
        {"product_id": pid, "quantity": 3},
        {"product_id": pid, "quantity": 3},
    ]})
    assert r.status_code == 409
    assert client.get(f"/products/{pid}").json()["stock"] == 5
    # toplam 5 == 5 → 201, stok 0
    r = client.post("/orders", json={"items": [
        {"product_id": pid, "quantity": 2},
        {"product_id": pid, "quantity": 3},
    ]})
    assert r.status_code == 201
    assert client.get(f"/products/{pid}").json()["stock"] == 0


def test_price_snapshot(client):
    pid = _mk_product(client, sku="SNAP", price=500, stock=10)
    oid = client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": 2}]}).json()["id"]
    # fiyatı değiştir
    assert client.patch(f"/products/{pid}", json={"price_cents": 999}).status_code == 200
    # geçmiş sipariş değişmez
    body = client.get(f"/orders/{oid}").json()
    assert body["items"][0]["unit_price_cents"] == 500
    assert body["total_cents"] == 1000


def test_cancel_restores_stock_and_idempotent(client):
    pid = _mk_product(client, sku="CAN", stock=10)
    oid = client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": 4}]}).json()["id"]
    assert client.get(f"/products/{pid}").json()["stock"] == 6
    r = client.post(f"/orders/{oid}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    assert client.get(f"/products/{pid}").json()["stock"] == 10
    # çift iptal → 409, stok iki kat yüklenmez
    assert client.post(f"/orders/{oid}/cancel").status_code == 409
    assert client.get(f"/products/{pid}").json()["stock"] == 10


def test_order_not_found(client):
    assert client.get("/orders/999").status_code == 404
    assert client.post("/orders/999/cancel").status_code == 404


def test_product_not_found(client):
    assert client.post("/orders", json={
        "items": [{"product_id": 999, "quantity": 1}]}).status_code == 404


def test_validation(client):
    pid = _mk_product(client, sku="VAL")
    assert client.post("/orders", json={"items": []}).status_code == 422
    assert client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": 0}]}).status_code == 422
    assert client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": -1}]}).status_code == 422


def test_referential_integrity_delete_409(client):
    pid = _mk_product(client, sku="REF", stock=5)
    client.post("/orders", json={"items": [{"product_id": pid, "quantity": 1}]})
    assert client.delete(f"/products/{pid}").status_code == 409
    # referansı olmayan ürün silinebilir
    free = _mk_product(client, sku="FREE")
    assert client.delete(f"/products/{free}").status_code == 204


def test_revenue_by_category(client):
    a = _mk_product(client, sku="RA", price=100, stock=10, category="cat_a")
    b = _mk_product(client, sku="RB", price=200, stock=10, category="cat_b")
    client.post("/orders", json={"items": [{"product_id": a, "quantity": 2}]})  # 200
    oid = client.post("/orders", json={
        "items": [{"product_id": b, "quantity": 3}]}).json()["id"]  # 600
    rep = client.get("/reports/revenue-by-category").json()
    assert rep == {"cat_a": 200, "cat_b": 600}
    # iptal edilen sipariş rapora girmez
    client.post(f"/orders/{oid}/cancel")
    assert client.get("/reports/revenue-by-category").json() == {"cat_a": 200}
