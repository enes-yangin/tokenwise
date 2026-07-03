"""Order endpoint testleri — tüm edge case'ler dahil."""
import pytest


# --- helpers ---

def make_product(client, name="Widget", sku="W1", price_cents=1000, stock=10, category="electronics"):
    r = client.post("/products", json={
        "name": name, "sku": sku, "price_cents": price_cents,
        "stock": stock, "category": category,
    })
    assert r.status_code == 201
    return r.json()


# --- POST /orders ---

def test_create_order_basic(client):
    p = make_product(client)
    r = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 2}]})
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert len(data["items"]) == 1
    assert data["items"][0]["unit_price_cents"] == 1000
    assert data["total_cents"] == 2000
    assert "created_at" in data


def test_create_order_reduces_stock(client):
    p = make_product(client)
    client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 3}]})
    updated = client.get(f"/products/{p['id']}").json()
    assert updated["stock"] == 7


def test_create_order_404_unknown_product(client):
    r = client.post("/orders", json={"items": [{"product_id": 9999, "quantity": 1}]})
    assert r.status_code == 404


def test_create_order_409_insufficient_stock(client):
    p = make_product(client, stock=2)
    r = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 5}]})
    assert r.status_code == 409


def test_create_order_atomic_no_partial_deduction(client):
    """Stok yetersizse hiçbir ürünün stoğu düşmemeli."""
    p1 = make_product(client, name="A", sku="A1", stock=10)
    p2 = make_product(client, name="B", sku="B1", stock=1)
    r = client.post("/orders", json={"items": [
        {"product_id": p1["id"], "quantity": 5},
        {"product_id": p2["id"], "quantity": 5},  # yetersiz
    ]})
    assert r.status_code == 409
    # p1 stoğu değişmemiş olmalı
    assert client.get(f"/products/{p1['id']}").json()["stock"] == 10


def test_create_order_same_product_multiple_rows_aggregated(client):
    """Aynı ürün 2 satırda → toplam miktar kontrol edilir."""
    p = make_product(client, stock=5)
    # Toplam 6 → yetersiz
    r = client.post("/orders", json={"items": [
        {"product_id": p["id"], "quantity": 3},
        {"product_id": p["id"], "quantity": 3},
    ]})
    assert r.status_code == 409
    # Stok değişmemiş
    assert client.get(f"/products/{p['id']}").json()["stock"] == 5


def test_create_order_same_product_multiple_rows_within_stock(client):
    """Aynı ürün 2 satırda → toplam stok içindeyse başarı."""
    p = make_product(client, stock=10)
    r = client.post("/orders", json={"items": [
        {"product_id": p["id"], "quantity": 3},
        {"product_id": p["id"], "quantity": 3},
    ]})
    assert r.status_code == 201
    assert client.get(f"/products/{p['id']}").json()["stock"] == 4


def test_create_order_422_empty_items(client):
    r = client.post("/orders", json={"items": []})
    assert r.status_code == 422


def test_create_order_422_zero_quantity(client):
    p = make_product(client)
    r = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 0}]})
    assert r.status_code == 422


def test_create_order_422_negative_quantity(client):
    p = make_product(client)
    r = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": -1}]})
    assert r.status_code == 422


# --- Price snapshot ---

def test_price_snapshot_not_affected_by_patch(client):
    p = make_product(client, price_cents=500)
    r = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 1}]})
    order_id = r.json()["id"]
    # Fiyatı değiştir
    client.patch(f"/products/{p['id']}", json={"price_cents": 9999})
    # Sipariş total'i değişmemeli
    order = client.get(f"/orders/{order_id}").json()
    assert order["items"][0]["unit_price_cents"] == 500
    assert order["total_cents"] == 500


# --- GET /orders/{id} ---

def test_get_order_200(client):
    p = make_product(client)
    created = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 1}]}).json()
    r = client.get(f"/orders/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_get_order_404(client):
    r = client.get("/orders/9999")
    assert r.status_code == 404


# --- POST /orders/{id}/cancel ---

def test_cancel_order(client):
    p = make_product(client, stock=10)
    order = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 3}]}).json()
    r = client.post(f"/orders/{order['id']}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    # Stok geri yüklendi
    assert client.get(f"/products/{p['id']}").json()["stock"] == 10


def test_cancel_order_idempotency_409(client):
    p = make_product(client, stock=10)
    order = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 3}]}).json()
    client.post(f"/orders/{order['id']}/cancel")
    # İkinci iptal → 409
    r = client.post(f"/orders/{order['id']}/cancel")
    assert r.status_code == 409
    # Stok iki kez yüklenmemiş
    assert client.get(f"/products/{p['id']}").json()["stock"] == 10


def test_cancel_order_404(client):
    r = client.post("/orders/9999/cancel")
    assert r.status_code == 404


# --- GET /reports/revenue-by-category ---

def test_revenue_by_category(client):
    p1 = make_product(client, name="A", sku="A1", price_cents=1000, stock=10, category="electronics")
    p2 = make_product(client, name="B", sku="B1", price_cents=500, stock=10, category="books")
    client.post("/orders", json={"items": [{"product_id": p1["id"], "quantity": 2}]})
    client.post("/orders", json={"items": [{"product_id": p2["id"], "quantity": 4}]})
    r = client.get("/reports/revenue-by-category")
    assert r.status_code == 200
    data = r.json()
    assert data["electronics"] == 2000
    assert data["books"] == 2000


def test_revenue_excludes_cancelled(client):
    p = make_product(client, price_cents=1000, stock=10, category="electronics")
    order = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 3}]}).json()
    client.post(f"/orders/{order['id']}/cancel")
    r = client.get("/reports/revenue-by-category")
    assert r.status_code == 200
    assert "electronics" not in r.json()


def test_revenue_empty(client):
    r = client.get("/reports/revenue-by-category")
    assert r.status_code == 200
    assert r.json() == {}


# --- Referential integrity: DELETE /products/{id} ---

def test_delete_product_referenced_by_order_409(client):
    p = make_product(client)
    client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 1}]})
    r = client.delete(f"/products/{p['id']}")
    assert r.status_code == 409


def test_delete_product_not_referenced_succeeds(client):
    p = make_product(client)
    r = client.delete(f"/products/{p['id']}")
    assert r.status_code == 204


# --- Integer cents, no floats ---

def test_total_cents_is_integer(client):
    p = make_product(client, price_cents=333)
    r = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 3}]})
    assert r.status_code == 201
    data = r.json()
    assert isinstance(data["total_cents"], int)
    assert data["total_cents"] == 999
