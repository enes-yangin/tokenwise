"""Order endpoint testleri — spec edge case'leri."""


def _mk_product(client, sku, price=500, stock=10, category="tools"):
    r = client.post("/products", json={
        "name": "P", "sku": sku, "price_cents": price,
        "stock": stock, "category": category})
    assert r.status_code == 201
    return r.json()["id"]


def test_create_order_snapshots_price_and_decrements_stock(client):
    pid = _mk_product(client, "O1", price=300, stock=5)
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 2}]})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    assert body["items"] == [
        {"product_id": pid, "quantity": 2, "unit_price_cents": 300}
    ]
    assert body["total_cents"] == 600
    assert "created_at" in body
    assert client.get(f"/products/{pid}").json()["stock"] == 3


def test_insufficient_stock_409_no_partial_decrement(client):
    p1 = _mk_product(client, "O2a", stock=5)
    p2 = _mk_product(client, "O2b", stock=1)
    r = client.post("/orders", json={"items": [
        {"product_id": p1, "quantity": 2},
        {"product_id": p2, "quantity": 5},
    ]})
    assert r.status_code == 409
    # Hiçbir stok düşmemeli (atomik).
    assert client.get(f"/products/{p1}").json()["stock"] == 5
    assert client.get(f"/products/{p2}").json()["stock"] == 1


def test_same_product_multiple_lines_summed(client):
    pid = _mk_product(client, "O3", stock=3)
    r = client.post("/orders", json={"items": [
        {"product_id": pid, "quantity": 2},
        {"product_id": pid, "quantity": 2},
    ]})
    assert r.status_code == 409  # toplam 4 > 3
    assert client.get(f"/products/{pid}").json()["stock"] == 3

    r2 = client.post("/orders", json={"items": [
        {"product_id": pid, "quantity": 1},
        {"product_id": pid, "quantity": 2},
    ]})
    assert r2.status_code == 201
    assert client.get(f"/products/{pid}").json()["stock"] == 0


def test_price_snapshot_immune_to_later_patch(client):
    pid = _mk_product(client, "O4", price=300, stock=5)
    oid = client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": 2}]}).json()["id"]
    client.patch(f"/products/{pid}", json={"price_cents": 999})
    body = client.get(f"/orders/{oid}").json()
    assert body["items"][0]["unit_price_cents"] == 300
    assert body["total_cents"] == 600


def test_cancel_restocks_and_idempotent(client):
    pid = _mk_product(client, "O5", stock=5)
    oid = client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": 3}]}).json()["id"]
    assert client.get(f"/products/{pid}").json()["stock"] == 2

    r = client.post(f"/orders/{oid}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    assert client.get(f"/products/{pid}").json()["stock"] == 5

    # İkinci iptal → 409, stok iki kat yüklenmez.
    r2 = client.post(f"/orders/{oid}/cancel")
    assert r2.status_code == 409
    assert client.get(f"/products/{pid}").json()["stock"] == 5


def test_order_not_found_404(client):
    assert client.get("/orders/9999").status_code == 404
    assert client.post("/orders/9999/cancel").status_code == 404


def test_product_not_found_404(client):
    assert client.post("/orders", json={
        "items": [{"product_id": 9999, "quantity": 1}]}).status_code == 404


def test_validation_422(client):
    pid = _mk_product(client, "O6")
    assert client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": 0}]}).status_code == 422
    assert client.post("/orders", json={"items": []}).status_code == 422


def test_delete_referenced_product_409(client):
    pid = _mk_product(client, "O7", stock=5)
    client.post("/orders", json={"items": [{"product_id": pid, "quantity": 1}]})
    assert client.delete(f"/products/{pid}").status_code == 409
    # Referanssız ürün hâlâ silinebilir.
    pid2 = _mk_product(client, "O7b")
    assert client.delete(f"/products/{pid2}").status_code == 204


def test_revenue_by_category_excludes_cancelled(client):
    a = _mk_product(client, "R1", price=100, stock=10, category="alpha")
    b = _mk_product(client, "R2", price=200, stock=10, category="beta")
    client.post("/orders", json={"items": [{"product_id": a, "quantity": 2}]})  # 200 alpha
    oid = client.post("/orders", json={
        "items": [{"product_id": b, "quantity": 3}]}).json()["id"]  # 600 beta
    client.post(f"/orders/{oid}/cancel")  # iptal → sayılmaz
    rep = client.get("/reports/revenue-by-category").json()
    assert rep == {"alpha": 200}
