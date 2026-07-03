"""Bağımsız jüri — orders feature'ını objektif test eder (agent'lar görmedi).

Çalıştırma: hedef agent dizininde, APP_DB=:memory: ile.
  cd <agent_dir> && APP_DB=:memory: <python> -m pytest ../judge_orders.py -q
sys.path'e agent dizini eklenir; `app.main` import edilir.
"""
import os
import sys
import uuid

import pytest

os.environ["APP_DB"] = ":memory:"
_TARGET = os.environ["JUDGE_TARGET"]
sys.path.insert(0, _TARGET)

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


def _sku():
    return "SKU-" + uuid.uuid4().hex[:12]


def _mk_product(client, price=100, stock=10, category=None):
    r = client.post("/products", json={
        "name": "p", "sku": _sku(), "price_cents": price,
        "stock": stock, "category": category or ("CAT-" + uuid.uuid4().hex[:8])})
    assert r.status_code == 201, (r.status_code, r.text)
    return r.json()


# --- temel sağlık ---
def test_create_order_basic(client):
    p = _mk_product(client, price=250, stock=5)
    r = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 2}]})
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["total_cents"] == 500
    assert b["status"] == "pending"
    assert client.get(f"/products/{p['id']}").json()["stock"] == 3


# --- 1: atomik stok ---
def test_atomic_no_partial(client):
    p1 = _mk_product(client, stock=10)
    p2 = _mk_product(client, stock=1)
    r = client.post("/orders", json={"items": [
        {"product_id": p1["id"], "quantity": 5},
        {"product_id": p2["id"], "quantity": 9}]})
    assert r.status_code == 409
    assert client.get(f"/products/{p1['id']}").json()["stock"] == 10
    assert client.get(f"/products/{p2['id']}").json()["stock"] == 1


def test_atomic_duplicate_lines(client):
    p = _mk_product(client, stock=5)
    r = client.post("/orders", json={"items": [
        {"product_id": p["id"], "quantity": 3},
        {"product_id": p["id"], "quantity": 3}]})
    assert r.status_code == 409
    assert client.get(f"/products/{p['id']}").json()["stock"] == 5


# --- 2: fiyat snapshot ---
def test_price_snapshot(client):
    p = _mk_product(client, price=100, stock=10)
    o = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 2}]}).json()
    assert o["total_cents"] == 200
    client.patch(f"/products/{p['id']}", json={"price_cents": 999})
    assert client.get(f"/orders/{o['id']}").json()["total_cents"] == 200


# --- 3: iptal idempotency ---
def test_cancel_idempotency(client):
    p = _mk_product(client, stock=10)
    o = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 3}]}).json()
    assert client.get(f"/products/{p['id']}").json()["stock"] == 7
    assert client.post(f"/orders/{o['id']}/cancel").status_code == 200
    assert client.get(f"/products/{p['id']}").json()["stock"] == 10
    assert client.post(f"/orders/{o['id']}/cancel").status_code == 409
    assert client.get(f"/products/{p['id']}").json()["stock"] == 10


# --- 4: para hassasiyeti ---
def test_money_integer(client):
    p = _mk_product(client, price=10, stock=100)
    o = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 3}]}).json()
    assert o["total_cents"] == 30 and isinstance(o["total_cents"], int)
    rev = client.get("/reports/revenue-by-category").json()
    assert all(isinstance(v, int) for v in rev.values())


# --- 5: referans bütünlüğü (mevcut katmana dokunur) ---
def test_referenced_product_undeletable(client):
    p = _mk_product(client, stock=10)
    client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 1}]})
    assert client.delete(f"/products/{p['id']}").status_code == 409


def test_unreferenced_product_deletable(client):
    p = _mk_product(client)
    assert client.delete(f"/products/{p['id']}").status_code == 204


# --- 6: validasyon ---
def test_zero_quantity_422(client):
    p = _mk_product(client, stock=10)
    assert client.post("/orders", json={"items": [
        {"product_id": p["id"], "quantity": 0}]}).status_code == 422


def test_empty_items_422(client):
    assert client.post("/orders", json={"items": []}).status_code == 422


# --- 7: 404 ---
def test_order_not_found(client):
    assert client.get("/orders/999999").status_code == 404


def test_product_not_found_in_order(client):
    assert client.post("/orders", json={"items": [
        {"product_id": 999999, "quantity": 1}]}).status_code == 404
