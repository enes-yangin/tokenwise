"""Bağımsız jüri test paketi — agent'lar bu kodu görmedi.

İki ayrı çalıştırma ile her iki agent'ın main.py'sine karşı çalışır:
  JUDGE_TARGET = agent dizini (sys.path'e eklenir)
  JUDGE_DB_ENV = o agent'ın DB izolasyon env değişkeni adı (:memory: verilir)

Her test kendi verisini benzersiz sku/kategori ile kurar → testler birbirinden
ve paylaşılan DB durumundan bağımsızdır. Her gizli edge case ayrı test sınıfında,
böylece "X/7 edge case geçti" objektif olarak ölçülür.
"""
import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

# --- target app'i yükle ----------------------------------------------------
_TARGET = os.environ["JUDGE_TARGET"]
_DB_ENV = os.environ["JUDGE_DB_ENV"]
os.environ[_DB_ENV] = ":memory:"
sys.path.insert(0, _TARGET)
import main  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(main.app) as c:
        yield c


def _sku():
    return "SKU-" + uuid.uuid4().hex[:12]


def _cat():
    return "CAT-" + uuid.uuid4().hex[:12]


def _mk_product(client, *, price=100, stock=10, category=None):
    body = {
        "name": "p",
        "sku": _sku(),
        "price_cents": price,
        "stock": stock,
        "category": category or _cat(),
    }
    r = client.post("/products", json=body)
    assert r.status_code == 201, (r.status_code, r.text)
    return r.json()


# === TEMEL KONTRAT (edge case dışı, sağlık kontrolü) =======================
class TestBasics:
    def test_create_and_get(self, client):
        p = _mk_product(client)
        r = client.get(f"/products/{p['id']}")
        assert r.status_code == 200
        assert r.json()["sku"] == p["sku"]

    def test_sku_conflict_409(self, client):
        p = _mk_product(client)
        r = client.post("/products", json={
            "name": "x", "sku": p["sku"], "price_cents": 1,
            "stock": 1, "category": "c",
        })
        assert r.status_code == 409

    def test_get_missing_404(self, client):
        r = client.get("/products/99999999")
        assert r.status_code == 404

    def test_order_and_total(self, client):
        p = _mk_product(client, price=250, stock=5)
        r = client.post("/orders", json={"items": [
            {"product_id": p["id"], "quantity": 2}]})
        assert r.status_code == 201
        body = r.json()
        assert body["total_cents"] == 500
        assert body["status"] == "pending"


# === EDGE CASE 1: Atomik stok düşümü ======================================
class TestEdge1_AtomicStock:
    def test_partial_order_no_stock_change(self, client):
        p1 = _mk_product(client, stock=10)
        p2 = _mk_product(client, stock=1)
        # p1 yeterli, p2 yetersiz → tüm sipariş 409, hiçbir stok değişmez
        r = client.post("/orders", json={"items": [
            {"product_id": p1["id"], "quantity": 5},
            {"product_id": p2["id"], "quantity": 9},
        ]})
        assert r.status_code == 409
        assert client.get(f"/products/{p1['id']}").json()["stock"] == 10
        assert client.get(f"/products/{p2['id']}").json()["stock"] == 1

    def test_duplicate_lines_aggregate(self, client):
        # Aynı ürün iki satırda toplam stoğu aşıyorsa → 409
        p = _mk_product(client, stock=5)
        r = client.post("/orders", json={"items": [
            {"product_id": p["id"], "quantity": 3},
            {"product_id": p["id"], "quantity": 3},
        ]})
        assert r.status_code == 409
        assert client.get(f"/products/{p['id']}").json()["stock"] == 5


# === EDGE CASE 2: Fiyat snapshot'ı ========================================
class TestEdge2_PriceSnapshot:
    def test_total_frozen_after_price_change(self, client):
        p = _mk_product(client, price=100, stock=10)
        order = client.post("/orders", json={"items": [
            {"product_id": p["id"], "quantity": 2}]}).json()
        assert order["total_cents"] == 200
        # fiyatı değiştir
        client.patch(f"/products/{p['id']}", json={"price_cents": 999})
        # geçmiş sipariş toplamı DEĞİŞMEMELİ
        again = client.get(f"/orders/{order['id']}").json()
        assert again["total_cents"] == 200


# === EDGE CASE 3: İptal idempotency =======================================
class TestEdge3_CancelIdempotency:
    def test_double_cancel_no_double_restock(self, client):
        p = _mk_product(client, stock=10)
        order = client.post("/orders", json={"items": [
            {"product_id": p["id"], "quantity": 3}]}).json()
        assert client.get(f"/products/{p['id']}").json()["stock"] == 7
        # ilk iptal → stok 10'a döner
        r1 = client.post(f"/orders/{order['id']}/cancel")
        assert r1.status_code == 200
        assert client.get(f"/products/{p['id']}").json()["stock"] == 10
        # ikinci iptal → 409, stok 13 OLMAMALI
        r2 = client.post(f"/orders/{order['id']}/cancel")
        assert r2.status_code == 409
        assert client.get(f"/products/{p['id']}").json()["stock"] == 10


# === EDGE CASE 4: Para hassasiyeti (int cents) ============================
class TestEdge4_MoneyPrecision:
    def test_totals_are_exact_integers(self, client):
        # float toplama 0.1+0.2 problemi; cents int olduğundan tam olmalı
        p = _mk_product(client, price=10, stock=100)  # 10 cents
        order = client.post("/orders", json={"items": [
            {"product_id": p["id"], "quantity": 3}]}).json()
        assert order["total_cents"] == 30
        assert isinstance(order["total_cents"], int)
        # revenue de int ve tam
        rev = client.get("/reports/revenue-by-category").json()
        assert all(isinstance(v, int) for v in rev.values())


# === EDGE CASE 5: Sayfalama sınırları =====================================
class TestEdge5_Pagination:
    def test_offset_past_end_empty(self, client):
        cat = _cat()
        for _ in range(3):
            _mk_product(client, category=cat)
        r = client.get(f"/products?category={cat}&limit=50&offset=100")
        assert r.status_code == 200
        assert r.json() == []

    def test_limit_offset_window(self, client):
        cat = _cat()
        for _ in range(3):
            _mk_product(client, category=cat)
        assert len(client.get(f"/products?category={cat}&limit=2&offset=0").json()) == 2
        assert len(client.get(f"/products?category={cat}&limit=2&offset=2").json()) == 1


# === EDGE CASE 6: Referans bütünlüğü ======================================
class TestEdge6_ReferentialIntegrity:
    def test_referenced_product_undeletable(self, client):
        p = _mk_product(client, stock=10)
        client.post("/orders", json={"items": [
            {"product_id": p["id"], "quantity": 1}]})
        r = client.delete(f"/products/{p['id']}")
        assert r.status_code == 409

    def test_unreferenced_product_deletable(self, client):
        p = _mk_product(client)
        r = client.delete(f"/products/{p['id']}")
        assert r.status_code == 204


# === EDGE CASE 7: Validasyon ==============================================
class TestEdge7_Validation:
    def test_negative_price_422(self, client):
        r = client.post("/products", json={
            "name": "x", "sku": _sku(), "price_cents": -1,
            "stock": 5, "category": "c"})
        assert r.status_code == 422

    def test_negative_stock_422(self, client):
        r = client.post("/products", json={
            "name": "x", "sku": _sku(), "price_cents": 5,
            "stock": -3, "category": "c"})
        assert r.status_code == 422

    def test_zero_quantity_order_422(self, client):
        p = _mk_product(client, stock=10)
        r = client.post("/orders", json={"items": [
            {"product_id": p["id"], "quantity": 0}]})
        assert r.status_code == 422

    def test_empty_items_422(self, client):
        r = client.post("/orders", json={"items": []})
        assert r.status_code == 422
