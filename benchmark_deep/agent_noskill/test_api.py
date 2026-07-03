"""Tests for the Inventory & Order API."""
import os

import pytest

os.environ["INVENTORY_DB"] = ":memory:"

import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client():
    main.reset_db()
    with TestClient(main.app) as c:
        yield c


def _mk_product(client, sku="ABC", price=1000, stock=10, category="cat-a", name="Widget"):
    r = client.post(
        "/products",
        json={
            "name": name,
            "sku": sku,
            "price_cents": price,
            "stock": stock,
            "category": category,
        },
    )
    return r


# --- Products ---------------------------------------------------------------
def test_create_product(client):
    r = _mk_product(client)
    assert r.status_code == 201
    body = r.json()
    assert body["id"] >= 1
    assert body["sku"] == "ABC"
    assert body["stock"] == 10


def test_create_duplicate_sku_conflict(client):
    _mk_product(client, sku="DUP")
    r = _mk_product(client, sku="DUP")
    assert r.status_code == 409


def test_create_negative_price_422(client):
    r = _mk_product(client, price=-5)
    assert r.status_code == 422


def test_create_negative_stock_422(client):
    r = _mk_product(client, stock=-1)
    assert r.status_code == 422


def test_create_missing_field_422(client):
    r = client.post("/products", json={"name": "x", "sku": "y"})
    assert r.status_code == 422


def test_get_product_404(client):
    assert client.get("/products/999").status_code == 404


def test_get_product_ok(client):
    pid = _mk_product(client).json()["id"]
    r = client.get(f"/products/{pid}")
    assert r.status_code == 200
    assert r.json()["id"] == pid


def test_patch_product(client):
    pid = _mk_product(client).json()["id"]
    r = client.patch(f"/products/{pid}", json={"price_cents": 200})
    assert r.status_code == 200
    assert r.json()["price_cents"] == 200


def test_patch_product_404(client):
    assert client.patch("/products/999", json={"price_cents": 1}).status_code == 404


def test_patch_negative_422(client):
    pid = _mk_product(client).json()["id"]
    assert client.patch(f"/products/{pid}", json={"stock": -1}).status_code == 422


def test_list_products_filter_and_pagination(client):
    _mk_product(client, sku="a", category="x")
    _mk_product(client, sku="b", category="x")
    _mk_product(client, sku="c", category="y")
    assert len(client.get("/products").json()) == 3
    assert len(client.get("/products?category=x").json()) == 2
    assert len(client.get("/products?limit=1").json()) == 1
    # offset past the end -> empty list, not error
    r = client.get("/products?offset=100")
    assert r.status_code == 200
    assert r.json() == []


def test_delete_product(client):
    pid = _mk_product(client).json()["id"]
    assert client.delete(f"/products/{pid}").status_code == 204
    assert client.get(f"/products/{pid}").status_code == 404


def test_delete_product_404(client):
    assert client.delete("/products/999").status_code == 404


def test_delete_referenced_product_409(client):
    pid = _mk_product(client, stock=5).json()["id"]
    client.post("/orders", json={"items": [{"product_id": pid, "quantity": 1}]})
    assert client.delete(f"/products/{pid}").status_code == 409


# --- Orders -----------------------------------------------------------------
def test_create_order_ok(client):
    pid = _mk_product(client, price=1000, stock=10).json()["id"]
    r = client.post(
        "/orders", json={"items": [{"product_id": pid, "quantity": 3}]}
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    assert body["total_cents"] == 3000
    assert "created_at" in body
    # stock decremented
    assert client.get(f"/products/{pid}").json()["stock"] == 7


def test_create_order_empty_items_422(client):
    assert client.post("/orders", json={"items": []}).status_code == 422


def test_create_order_zero_quantity_422(client):
    pid = _mk_product(client).json()["id"]
    r = client.post(
        "/orders", json={"items": [{"product_id": pid, "quantity": 0}]}
    )
    assert r.status_code == 422


def test_create_order_unknown_product_404(client):
    r = client.post(
        "/orders", json={"items": [{"product_id": 999, "quantity": 1}]}
    )
    assert r.status_code == 404


def test_create_order_insufficient_stock_409(client):
    pid = _mk_product(client, stock=2).json()["id"]
    r = client.post(
        "/orders", json={"items": [{"product_id": pid, "quantity": 5}]}
    )
    assert r.status_code == 409


def test_atomic_stock_no_partial_decrement(client):
    p1 = _mk_product(client, sku="p1", stock=10).json()["id"]
    p2 = _mk_product(client, sku="p2", stock=1).json()["id"]
    r = client.post(
        "/orders",
        json={
            "items": [
                {"product_id": p1, "quantity": 5},
                {"product_id": p2, "quantity": 5},  # insufficient
            ]
        },
    )
    assert r.status_code == 409
    # neither stock changed
    assert client.get(f"/products/{p1}").json()["stock"] == 10
    assert client.get(f"/products/{p2}").json()["stock"] == 1


def test_price_snapshot(client):
    pid = _mk_product(client, price=1000, stock=10).json()["id"]
    oid = client.post(
        "/orders", json={"items": [{"product_id": pid, "quantity": 2}]}
    ).json()["id"]
    # change price after order
    client.patch(f"/products/{pid}", json={"price_cents": 9999})
    # historical total unchanged
    assert client.get(f"/orders/{oid}").json()["total_cents"] == 2000


def test_get_order_404(client):
    assert client.get("/orders/999").status_code == 404


def test_cancel_order_restores_stock(client):
    pid = _mk_product(client, stock=10).json()["id"]
    oid = client.post(
        "/orders", json={"items": [{"product_id": pid, "quantity": 4}]}
    ).json()["id"]
    assert client.get(f"/products/{pid}").json()["stock"] == 6
    r = client.post(f"/orders/{oid}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    assert client.get(f"/products/{pid}").json()["stock"] == 10


def test_cancel_order_404(client):
    assert client.post("/orders/999/cancel").status_code == 404


def test_cancel_idempotency_409(client):
    pid = _mk_product(client, stock=10).json()["id"]
    oid = client.post(
        "/orders", json={"items": [{"product_id": pid, "quantity": 4}]}
    ).json()["id"]
    assert client.post(f"/orders/{oid}/cancel").status_code == 200
    # second cancel -> 409, stock not restored twice
    assert client.post(f"/orders/{oid}/cancel").status_code == 409
    assert client.get(f"/products/{pid}").json()["stock"] == 10


# --- Reports ----------------------------------------------------------------
def test_low_stock_default_threshold(client):
    _mk_product(client, sku="low", stock=5)
    _mk_product(client, sku="high", stock=50)
    skus = {p["sku"] for p in client.get("/reports/low-stock").json()}
    assert skus == {"low"}


def test_low_stock_custom_threshold(client):
    _mk_product(client, sku="a", stock=5)
    _mk_product(client, sku="b", stock=20)
    skus = {p["sku"] for p in client.get("/reports/low-stock?threshold=30").json()}
    assert skus == {"a", "b"}


def test_revenue_by_category(client):
    pa = _mk_product(client, sku="a", price=1000, stock=10, category="cat-a").json()["id"]
    pb = _mk_product(client, sku="b", price=500, stock=10, category="cat-b").json()["id"]
    client.post("/orders", json={"items": [{"product_id": pa, "quantity": 2}]})
    client.post("/orders", json={"items": [{"product_id": pb, "quantity": 3}]})
    rev = client.get("/reports/revenue-by-category").json()
    assert rev == {"cat-a": 2000, "cat-b": 1500}


def test_revenue_excludes_cancelled(client):
    pa = _mk_product(client, sku="a", price=1000, stock=10, category="cat-a").json()["id"]
    oid = client.post(
        "/orders", json={"items": [{"product_id": pa, "quantity": 2}]}
    ).json()["id"]
    client.post(f"/orders/{oid}/cancel")
    assert client.get("/reports/revenue-by-category").json() == {}
