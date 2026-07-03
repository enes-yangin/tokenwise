import os

os.environ["DATABASE_URL"] = ":memory:"

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client():
    # Each TestClient context triggers the app lifespan, which calls init_db()
    # and rebuilds a fresh :memory: DB -> full isolation per test.
    with TestClient(main.app) as c:
        yield c


def make_product(client, **over):
    body = {
        "name": "Widget",
        "sku": "SKU-1",
        "price_cents": 1000,
        "stock": 100,
        "category": "tools",
    }
    body.update(over)
    return client.post("/products", json=body)


# --------------------------------------------------------------------------- #
# Products
# --------------------------------------------------------------------------- #
def test_create_product_201(client):
    r = make_product(client)
    assert r.status_code == 201
    data = r.json()
    assert data["id"] > 0
    assert data["sku"] == "SKU-1"
    assert data["price_cents"] == 1000


def test_create_product_duplicate_sku_409(client):
    make_product(client)
    r = make_product(client, name="Other")
    assert r.status_code == 409


def test_create_product_missing_field_422(client):
    r = client.post("/products", json={"name": "x", "sku": "y"})
    assert r.status_code == 422


def test_get_product_404(client):
    assert client.get("/products/999").status_code == 404


def test_get_product_200(client):
    pid = make_product(client).json()["id"]
    r = client.get(f"/products/{pid}")
    assert r.status_code == 200
    assert r.json()["id"] == pid


def test_list_products_filter_category(client):
    make_product(client, sku="a", category="tools")
    make_product(client, sku="b", category="food")
    r = client.get("/products", params={"category": "food"})
    assert r.status_code == 200
    cats = {p["category"] for p in r.json()}
    assert cats == {"food"}


def test_patch_product_200(client):
    pid = make_product(client).json()["id"]
    r = client.patch(f"/products/{pid}", json={"price_cents": 200})
    assert r.status_code == 200
    assert r.json()["price_cents"] == 200


def test_patch_product_404(client):
    assert client.patch("/products/999", json={"price_cents": 1}).status_code == 404


def test_delete_product_204(client):
    pid = make_product(client).json()["id"]
    assert client.delete(f"/products/{pid}").status_code == 204
    assert client.get(f"/products/{pid}").status_code == 404


def test_delete_product_404(client):
    assert client.delete("/products/999").status_code == 404


# --------------------------------------------------------------------------- #
# Orders
# --------------------------------------------------------------------------- #
def test_create_order_201_and_stock_drop(client):
    pid = make_product(client, stock=10, price_cents=500).json()["id"]
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 3}]})
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert data["total_cents"] == 1500
    assert data["items"][0]["unit_price_cents"] == 500
    assert client.get(f"/products/{pid}").json()["stock"] == 7


def test_create_order_product_not_found_404(client):
    r = client.post("/orders", json={"items": [{"product_id": 999, "quantity": 1}]})
    assert r.status_code == 404


def test_create_order_empty_items_422(client):
    assert client.post("/orders", json={"items": []}).status_code == 422


def test_get_order_404(client):
    assert client.get("/orders/999").status_code == 404


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #
def test_low_stock_default_threshold(client):
    make_product(client, sku="low", stock=5)
    make_product(client, sku="high", stock=50)
    skus = {p["sku"] for p in client.get("/reports/low-stock").json()}
    assert skus == {"low"}


def test_revenue_by_category_excludes_cancelled(client):
    a = make_product(client, sku="a", category="tools", price_cents=100, stock=10).json()["id"]
    b = make_product(client, sku="b", category="food", price_cents=200, stock=10).json()["id"]
    o1 = client.post("/orders", json={"items": [{"product_id": a, "quantity": 2}]}).json()["id"]
    client.post("/orders", json={"items": [{"product_id": b, "quantity": 1}]})
    # cancel o1 -> tools revenue should disappear
    client.post(f"/orders/{o1}/cancel")
    rev = client.get("/reports/revenue-by-category").json()
    assert rev == {"food": 200}


# --------------------------------------------------------------------------- #
# 7 hidden edge cases
# --------------------------------------------------------------------------- #
def test_edge1_atomic_stock_no_partial_deduction(client):
    p1 = make_product(client, sku="p1", stock=5).json()["id"]
    p2 = make_product(client, sku="p2", stock=1).json()["id"]
    r = client.post(
        "/orders",
        json={"items": [{"product_id": p1, "quantity": 3}, {"product_id": p2, "quantity": 5}]},
    )
    assert r.status_code == 409
    # No stock changed at all.
    assert client.get(f"/products/{p1}").json()["stock"] == 5
    assert client.get(f"/products/{p2}").json()["stock"] == 1


def test_edge2_price_snapshot_unchanged_after_patch(client):
    pid = make_product(client, price_cents=1000, stock=10).json()["id"]
    oid = client.post(
        "/orders", json={"items": [{"product_id": pid, "quantity": 2}]}
    ).json()["id"]
    client.patch(f"/products/{pid}", json={"price_cents": 9999})
    order = client.get(f"/orders/{oid}").json()
    assert order["total_cents"] == 2000
    assert order["items"][0]["unit_price_cents"] == 1000


def test_edge3_cancel_idempotency(client):
    pid = make_product(client, stock=10).json()["id"]
    oid = client.post(
        "/orders", json={"items": [{"product_id": pid, "quantity": 4}]}
    ).json()["id"]
    assert client.get(f"/products/{pid}").json()["stock"] == 6
    assert client.post(f"/orders/{oid}/cancel").status_code == 200
    assert client.get(f"/products/{pid}").json()["stock"] == 10
    # Second cancel must 409 and NOT restock again.
    assert client.post(f"/orders/{oid}/cancel").status_code == 409
    assert client.get(f"/products/{pid}").json()["stock"] == 10


def test_edge4_money_precision_integer_only(client):
    pid = make_product(client, price_cents=333, stock=10).json()["id"]
    data = client.post(
        "/orders", json={"items": [{"product_id": pid, "quantity": 3}]}
    ).json()
    assert data["total_cents"] == 999
    assert isinstance(data["total_cents"], int)


def test_edge5_pagination_offset_beyond_end_empty(client):
    make_product(client, sku="only")
    r = client.get("/products", params={"limit": 10, "offset": 100})
    assert r.status_code == 200
    assert r.json() == []


def test_edge6_referential_integrity_delete_blocked(client):
    pid = make_product(client, stock=10).json()["id"]
    client.post("/orders", json={"items": [{"product_id": pid, "quantity": 1}]})
    assert client.delete(f"/products/{pid}").status_code == 409


def test_edge7_validation_negatives_422(client):
    assert make_product(client, price_cents=-1).status_code == 422
    assert make_product(client, stock=-1).status_code == 422
    pid_ok = make_product(client, sku="ok", stock=10).json()["id"]
    r = client.post(
        "/orders", json={"items": [{"product_id": pid_ok, "quantity": -2}]}
    )
    assert r.status_code == 422
