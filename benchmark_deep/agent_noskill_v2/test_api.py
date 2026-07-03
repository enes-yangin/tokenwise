import importlib
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DB_PATH", ":memory:")
    import main
    importlib.reload(main)
    main._memory_conn = None  # ensure a fresh in-memory DB per test
    with TestClient(main.app) as c:
        yield c
    main._memory_conn = None


def _mk_product(client, **over):
    body = {
        "name": "Widget",
        "sku": "SKU-1",
        "price_cents": 1000,
        "stock": 5,
        "category": "tools",
    }
    body.update(over)
    return client.post("/products", json=body)


# ---------- Products ----------
def test_create_product_201(client):
    r = _mk_product(client)
    assert r.status_code == 201
    data = r.json()
    assert data["id"] >= 1
    assert data["sku"] == "SKU-1"


def test_create_duplicate_sku_409(client):
    _mk_product(client)
    r = _mk_product(client)
    assert r.status_code == 409


def test_create_negative_price_422(client):
    r = _mk_product(client, price_cents=-1)
    assert r.status_code == 422


def test_create_negative_stock_422(client):
    r = _mk_product(client, stock=-1)
    assert r.status_code == 422


def test_create_missing_field_422(client):
    r = client.post("/products", json={"name": "x", "sku": "y"})
    assert r.status_code == 422


def test_get_product_404(client):
    assert client.get("/products/999").status_code == 404


def test_get_product_200(client):
    pid = _mk_product(client).json()["id"]
    r = client.get(f"/products/{pid}")
    assert r.status_code == 200
    assert r.json()["id"] == pid


def test_list_filter_by_category(client):
    _mk_product(client, sku="a", category="tools")
    _mk_product(client, sku="b", category="food")
    r = client.get("/products", params={"category": "food"})
    assert r.status_code == 200
    cats = {p["category"] for p in r.json()}
    assert cats == {"food"}


def test_list_pagination_offset_out_of_range(client):
    _mk_product(client, sku="a")
    r = client.get("/products", params={"offset": 100})
    assert r.status_code == 200
    assert r.json() == []


def test_list_pagination_limit(client):
    for i in range(3):
        _mk_product(client, sku=f"s{i}")
    r = client.get("/products", params={"limit": 2})
    assert len(r.json()) == 2


def test_patch_product_200(client):
    pid = _mk_product(client).json()["id"]
    r = client.patch(f"/products/{pid}", json={"price_cents": 200})
    assert r.status_code == 200
    assert r.json()["price_cents"] == 200


def test_patch_product_404(client):
    assert client.patch("/products/999", json={"price_cents": 1}).status_code == 404


def test_delete_product_204(client):
    pid = _mk_product(client).json()["id"]
    assert client.delete(f"/products/{pid}").status_code == 204
    assert client.get(f"/products/{pid}").status_code == 404


def test_delete_product_404(client):
    assert client.delete("/products/999").status_code == 404


def test_delete_referenced_product_409(client):
    pid = _mk_product(client, stock=5).json()["id"]
    client.post("/orders", json={"items": [{"product_id": pid, "quantity": 1}]})
    assert client.delete(f"/products/{pid}").status_code == 409


# ---------- Orders ----------
def test_create_order_201_and_stock_decrement(client):
    pid = _mk_product(client, stock=5, price_cents=1000).json()["id"]
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 2}]})
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert data["total_cents"] == 2000
    assert data["items"][0]["unit_price_cents"] == 1000
    assert client.get(f"/products/{pid}").json()["stock"] == 3


def test_create_order_insufficient_stock_atomic_409(client):
    p1 = _mk_product(client, sku="a", stock=5).json()["id"]
    p2 = _mk_product(client, sku="b", stock=1).json()["id"]
    r = client.post(
        "/orders",
        json={"items": [
            {"product_id": p1, "quantity": 2},
            {"product_id": p2, "quantity": 5},
        ]},
    )
    assert r.status_code == 409
    # no partial decrement
    assert client.get(f"/products/{p1}").json()["stock"] == 5
    assert client.get(f"/products/{p2}").json()["stock"] == 1


def test_create_order_product_not_found_404(client):
    assert client.post("/orders", json={"items": [{"product_id": 999, "quantity": 1}]}).status_code == 404


def test_create_order_quantity_zero_422(client):
    pid = _mk_product(client).json()["id"]
    assert client.post("/orders", json={"items": [{"product_id": pid, "quantity": 0}]}).status_code == 422


def test_create_order_empty_items_422(client):
    assert client.post("/orders", json={"items": []}).status_code == 422


def test_get_order_404(client):
    assert client.get("/orders/999").status_code == 404


def test_price_snapshot_unchanged_after_patch(client):
    pid = _mk_product(client, stock=5, price_cents=1000).json()["id"]
    oid = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 1}]}).json()["id"]
    client.patch(f"/products/{pid}", json={"price_cents": 9999})
    assert client.get(f"/orders/{oid}").json()["total_cents"] == 1000


def test_cancel_restores_stock(client):
    pid = _mk_product(client, stock=5).json()["id"]
    oid = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 2}]}).json()["id"]
    assert client.get(f"/products/{pid}").json()["stock"] == 3
    r = client.post(f"/orders/{oid}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    assert client.get(f"/products/{pid}").json()["stock"] == 5


def test_cancel_404(client):
    assert client.post("/orders/999/cancel").status_code == 404


def test_cancel_idempotency_409_no_double_restore(client):
    pid = _mk_product(client, stock=5).json()["id"]
    oid = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 2}]}).json()["id"]
    client.post(f"/orders/{oid}/cancel")
    r = client.post(f"/orders/{oid}/cancel")
    assert r.status_code == 409
    assert client.get(f"/products/{pid}").json()["stock"] == 5  # not 7


# ---------- Reports ----------
def test_low_stock_default_threshold(client):
    _mk_product(client, sku="a", stock=5)
    _mk_product(client, sku="b", stock=50)
    r = client.get("/reports/low-stock")
    skus = {p["sku"] for p in r.json()}
    assert skus == {"a"}


def test_low_stock_custom_threshold(client):
    _mk_product(client, sku="a", stock=5)
    _mk_product(client, sku="b", stock=50)
    r = client.get("/reports/low-stock", params={"threshold": 100})
    assert len(r.json()) == 2


def test_revenue_by_category_excludes_cancelled(client):
    p1 = _mk_product(client, sku="a", stock=10, price_cents=1000, category="tools").json()["id"]
    p2 = _mk_product(client, sku="b", stock=10, price_cents=500, category="food").json()["id"]
    client.post("/orders", json={"items": [{"product_id": p1, "quantity": 2}]})  # 2000 tools
    oid2 = client.post("/orders", json={"items": [{"product_id": p2, "quantity": 3}]}).json()["id"]  # 1500 food
    client.post(f"/orders/{oid2}/cancel")
    r = client.get("/reports/revenue-by-category")
    assert r.json() == {"tools": 2000}
