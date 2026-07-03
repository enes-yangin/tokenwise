"""Orders endpoint testleri — acceptance check (verification-first)."""


def _mk_product(client, sku, price_cents=1000, stock=10, category="cat"):
    r = client.post("/products", json={
        "name": "P", "sku": sku, "price_cents": price_cents,
        "stock": stock, "category": category})
    assert r.status_code == 201
    return r.json()["id"]


def test_create_order_201_shape_and_stock_decrement(client):
    pid = _mk_product(client, "O1", price_cents=500, stock=10)
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 3}]})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    assert "id" in body and "created_at" in body
    assert body["items"] == [{"product_id": pid, "quantity": 3, "unit_price_cents": 500}]
    assert body["total_cents"] == 1500
    # stok düştü
    assert client.get(f"/products/{pid}").json()["stock"] == 7


def test_get_order_404(client):
    assert client.get("/orders/9999").status_code == 404


def test_create_order_unknown_product_404(client):
    r = client.post("/orders", json={"items": [{"product_id": 12345, "quantity": 1}]})
    assert r.status_code == 404


def test_quantity_must_be_positive_422(client):
    pid = _mk_product(client, "O2")
    assert client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": 0}]}).status_code == 422
    assert client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": -1}]}).status_code == 422


def test_empty_items_422(client):
    assert client.post("/orders", json={"items": []}).status_code == 422


def test_insufficient_stock_409_atomic(client):
    p_ok = _mk_product(client, "OK", stock=10)
    p_bad = _mk_product(client, "BAD", stock=1)
    r = client.post("/orders", json={"items": [
        {"product_id": p_ok, "quantity": 2},
        {"product_id": p_bad, "quantity": 5},
    ]})
    assert r.status_code == 409
    # kısmi düşüm olmamalı
    assert client.get(f"/products/{p_ok}").json()["stock"] == 10
    assert client.get(f"/products/{p_bad}").json()["stock"] == 1


def test_same_product_multiple_lines_summed(client):
    pid = _mk_product(client, "SUM", stock=5)
    # 3 + 3 = 6 > 5 → 409
    r = client.post("/orders", json={"items": [
        {"product_id": pid, "quantity": 3},
        {"product_id": pid, "quantity": 3},
    ]})
    assert r.status_code == 409
    assert client.get(f"/products/{pid}").json()["stock"] == 5


def test_price_snapshot_immune_to_later_patch(client):
    pid = _mk_product(client, "SNAP", price_cents=1000, stock=10)
    oid = client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": 2}]}).json()["id"]
    # fiyatı değiştir
    client.patch(f"/products/{pid}", json={"price_cents": 9999})
    body = client.get(f"/orders/{oid}").json()
    assert body["items"][0]["unit_price_cents"] == 1000
    assert body["total_cents"] == 2000


def test_cancel_restocks_and_idempotent(client):
    pid = _mk_product(client, "CAN", stock=10)
    oid = client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": 4}]}).json()["id"]
    assert client.get(f"/products/{pid}").json()["stock"] == 6
    r1 = client.post(f"/orders/{oid}/cancel")
    assert r1.status_code == 200
    assert r1.json()["status"] == "cancelled"
    assert client.get(f"/products/{pid}").json()["stock"] == 10
    # ikinci iptal → 409, stok iki kat yüklenmez
    r2 = client.post(f"/orders/{oid}/cancel")
    assert r2.status_code == 409
    assert client.get(f"/products/{pid}").json()["stock"] == 10


def test_cancel_unknown_order_404(client):
    assert client.post("/orders/9999/cancel").status_code == 404


def test_cannot_delete_referenced_product_409(client):
    pid = _mk_product(client, "REF", stock=10)
    client.post("/orders", json={"items": [{"product_id": pid, "quantity": 1}]})
    assert client.delete(f"/products/{pid}").status_code == 409
    # referansı olmayan ürün silinebilir
    free = _mk_product(client, "FREE")
    assert client.delete(f"/products/{free}").status_code == 204


def test_revenue_by_category_excludes_cancelled(client):
    p1 = _mk_product(client, "RC1", price_cents=1000, stock=10, category="alpha")
    p2 = _mk_product(client, "RC2", price_cents=200, stock=10, category="beta")
    client.post("/orders", json={"items": [{"product_id": p1, "quantity": 2}]})  # 2000 alpha
    o2 = client.post("/orders", json={
        "items": [{"product_id": p2, "quantity": 3}]}).json()["id"]  # 600 beta
    client.post("/orders", json={"items": [{"product_id": p1, "quantity": 1}]})  # 1000 alpha
    client.post(f"/orders/{o2}/cancel")  # beta iptal
    rep = client.get("/reports/revenue-by-category").json()
    assert rep.get("alpha") == 3000
    assert "beta" not in rep or rep.get("beta") == 0
