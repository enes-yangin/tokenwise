import pytest
import os
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Temiz DB ile TestClient."""
    # Her test için unique temp DB file
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    os.environ['DATABASE_URL'] = db_path
    tc = TestClient(app)

    yield tc

    # Cleanup
    try:
        Path(db_path).unlink()
    except:
        pass


class TestProducts:
    """Product endpoint'leri."""

    def test_create_product_success(self, client):
        """POST /products — başarılı oluşturma."""
        resp = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data['id'] is not None
        assert data['name'] == 'Widget'
        assert data['sku'] == 'WID-001'

    def test_create_product_duplicate_sku(self, client):
        """POST /products — sku zaten varsa 409."""
        client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        })
        resp = client.post('/products', json={
            'name': 'Another',
            'sku': 'WID-001',
            'price_cents': 500,
            'stock': 50,
            'category': 'electronics'
        })
        assert resp.status_code == 409

    def test_create_product_negative_price(self, client):
        """POST /products — negatif fiyat → 422."""
        resp = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': -100,
            'stock': 100,
            'category': 'electronics'
        })
        assert resp.status_code == 422

    def test_create_product_negative_stock(self, client):
        """POST /products — negatif stok → 422."""
        resp = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': -10,
            'category': 'electronics'
        })
        assert resp.status_code == 422

    def test_create_product_missing_field(self, client):
        """POST /products — eksik alan → 422."""
        resp = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000
            # stock eksik
        })
        assert resp.status_code == 422

    def test_get_product(self, client):
        """GET /products/{id} — başarılı."""
        create_resp = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        })
        product_id = create_resp.json()['id']
        resp = client.get(f'/products/{product_id}')
        assert resp.status_code == 200
        assert resp.json()['id'] == product_id

    def test_get_product_not_found(self, client):
        """GET /products/{id} — yoksa 404."""
        resp = client.get('/products/999')
        assert resp.status_code == 404

    def test_list_products(self, client):
        """GET /products — sayfalama."""
        client.post('/products', json={
            'name': 'Widget1',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        })
        client.post('/products', json={
            'name': 'Widget2',
            'sku': 'WID-002',
            'price_cents': 2000,
            'stock': 200,
            'category': 'electronics'
        })
        resp = client.get('/products?limit=1&offset=0')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

    def test_list_products_filter_by_category(self, client):
        """GET /products?category=X — kategoriye göre filtrele."""
        client.post('/products', json={
            'name': 'Widget1',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        })
        client.post('/products', json={
            'name': 'Book1',
            'sku': 'BOO-001',
            'price_cents': 500,
            'stock': 50,
            'category': 'books'
        })
        resp = client.get('/products?category=books')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['category'] == 'books'

    def test_list_products_offset_out_of_bounds(self, client):
        """Sayfalama sınırları — offset dışarıdaysa boş liste."""
        client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        })
        resp = client.get('/products?offset=100')
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_patch_product(self, client):
        """PATCH /products/{id} — kısmi güncelleme."""
        create_resp = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        })
        product_id = create_resp.json()['id']
        resp = client.patch(f'/products/{product_id}', json={
            'price_cents': 1500
        })
        assert resp.status_code == 200
        assert resp.json()['price_cents'] == 1500

    def test_patch_product_not_found(self, client):
        """PATCH /products/{id} — yoksa 404."""
        resp = client.patch('/products/999', json={'price_cents': 1500})
        assert resp.status_code == 404

    def test_delete_product(self, client):
        """DELETE /products/{id} — silme."""
        create_resp = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        })
        product_id = create_resp.json()['id']
        resp = client.delete(f'/products/{product_id}')
        assert resp.status_code == 204

    def test_delete_product_not_found(self, client):
        """DELETE /products/{id} — yoksa 404."""
        resp = client.delete('/products/999')
        assert resp.status_code == 404


class TestOrders:
    """Order endpoint'leri."""

    def test_create_order_success(self, client):
        """POST /orders — başarılı sipariş oluşturma."""
        prod = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        }).json()

        resp = client.post('/orders', json={
            'items': [{'product_id': prod['id'], 'quantity': 5}]
        })
        assert resp.status_code == 201
        order = resp.json()
        assert order['status'] == 'pending'
        assert order['total_cents'] == 5000
        assert len(order['items']) == 1
        assert order['items'][0]['unit_price_cents'] == 1000

    def test_create_order_decreases_stock(self, client):
        """POST /orders — stok düşer."""
        prod = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        }).json()

        client.post('/orders', json={
            'items': [{'product_id': prod['id'], 'quantity': 30}]
        })

        check = client.get(f'/products/{prod["id"]}').json()
        assert check['stock'] == 70

    def test_create_order_insufficient_stock_single_item(self, client):
        """POST /orders — stok yetersiz (tek kalem) → 409."""
        prod = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 10,
            'category': 'electronics'
        }).json()

        resp = client.post('/orders', json={
            'items': [{'product_id': prod['id'], 'quantity': 20}]
        })
        assert resp.status_code == 409

    def test_create_order_atomic_stock_deduction(self, client):
        """Edge case 1: Atomik stok düşümü — çok kalemli sipariş, bir kalem yetersizse hiçbir şey değişmez."""
        prod1 = client.post('/products', json={
            'name': 'Widget1',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        }).json()

        prod2 = client.post('/products', json={
            'name': 'Widget2',
            'sku': 'WID-002',
            'price_cents': 2000,
            'stock': 5,
            'category': 'electronics'
        }).json()

        # İlk ürün yeterli, ikinci yetersiz
        resp = client.post('/orders', json={
            'items': [
                {'product_id': prod1['id'], 'quantity': 30},
                {'product_id': prod2['id'], 'quantity': 10}  # yetersiz
            ]
        })
        assert resp.status_code == 409

        # Hiçbir ürünün stoğu değişmedi
        check1 = client.get(f'/products/{prod1["id"]}').json()
        check2 = client.get(f'/products/{prod2["id"]}').json()
        assert check1['stock'] == 100
        assert check2['stock'] == 5

    def test_create_order_price_snapshot(self, client):
        """Edge case 2: Fiyat snapshot'ı — sipariş sonrası ürün fiyatı değişse, eski sipariş tutarı değişmez."""
        prod = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        }).json()

        order = client.post('/orders', json={
            'items': [{'product_id': prod['id'], 'quantity': 5}]
        }).json()

        # Ürün fiyatını değiştir
        client.patch(f'/products/{prod["id"]}', json={'price_cents': 2000})

        # Sipariş tutarı değişmedi
        check = client.get(f'/orders/{order["id"]}').json()
        assert check['total_cents'] == 5000

    def test_create_order_negative_quantity(self, client):
        """POST /orders — negatif quantity → 422."""
        prod = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        }).json()

        resp = client.post('/orders', json={
            'items': [{'product_id': prod['id'], 'quantity': -5}]
        })
        assert resp.status_code == 422

    def test_create_order_zero_quantity(self, client):
        """POST /orders — quantity=0 → 422."""
        prod = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        }).json()

        resp = client.post('/orders', json={
            'items': [{'product_id': prod['id'], 'quantity': 0}]
        })
        assert resp.status_code == 422

    def test_create_order_empty_items(self, client):
        """POST /orders — boş items → 422."""
        resp = client.post('/orders', json={'items': []})
        assert resp.status_code == 422

    def test_create_order_product_not_found(self, client):
        """POST /orders — product_id yoksa → 404."""
        resp = client.post('/orders', json={
            'items': [{'product_id': 999, 'quantity': 5}]
        })
        assert resp.status_code == 404

    def test_get_order(self, client):
        """GET /orders/{id} — siparişi al."""
        prod = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        }).json()

        order = client.post('/orders', json={
            'items': [{'product_id': prod['id'], 'quantity': 5}]
        }).json()

        resp = client.get(f'/orders/{order["id"]}')
        assert resp.status_code == 200
        assert resp.json()['id'] == order['id']

    def test_get_order_not_found(self, client):
        """GET /orders/{id} — yoksa 404."""
        resp = client.get('/orders/999')
        assert resp.status_code == 404

    def test_cancel_order_success(self, client):
        """POST /orders/{id}/cancel — iptal et."""
        prod = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        }).json()

        order = client.post('/orders', json={
            'items': [{'product_id': prod['id'], 'quantity': 30}]
        }).json()

        resp = client.post(f'/orders/{order["id"]}/cancel')
        assert resp.status_code == 200
        assert resp.json()['status'] == 'cancelled'

        # Stok geri yüklendi
        check = client.get(f'/products/{prod["id"]}').json()
        assert check['stock'] == 100

    def test_cancel_order_idempotency(self, client):
        """Edge case 3: İptal idempotency — iki kez iptal → ikinci çağrı 409, stok iki kat yüklenmez."""
        prod = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        }).json()

        order = client.post('/orders', json={
            'items': [{'product_id': prod['id'], 'quantity': 30}]
        }).json()

        # İlk iptal — başarılı
        resp1 = client.post(f'/orders/{order["id"]}/cancel')
        assert resp1.status_code == 200

        check1 = client.get(f'/products/{prod["id"]}').json()
        assert check1['stock'] == 100

        # İkinci iptal — 409
        resp2 = client.post(f'/orders/{order["id"]}/cancel')
        assert resp2.status_code == 409

        # Stok hala 100 (iki kat yüklenmedi)
        check2 = client.get(f'/products/{prod["id"]}').json()
        assert check2['stock'] == 100

    def test_cancel_order_not_found(self, client):
        """POST /orders/{id}/cancel — sipariş yoksa 404."""
        resp = client.post('/orders/999/cancel')
        assert resp.status_code == 404


class TestReferentialIntegrity:
    """Edge case 6: Referans bütünlüğü."""

    def test_delete_product_with_order(self, client):
        """DELETE /products/{id} — siparişte referanslıysa silinemez → 409."""
        prod = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        }).json()

        client.post('/orders', json={
            'items': [{'product_id': prod['id'], 'quantity': 5}]
        })

        resp = client.delete(f'/products/{prod["id"]}')
        assert resp.status_code == 409

    def test_delete_product_after_order_cancel(self, client):
        """DELETE /products/{id} — iptal edilen sipariş referansı hala engeller (veya kaldırır, spec net değil)."""
        prod = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        }).json()

        order = client.post('/orders', json={
            'items': [{'product_id': prod['id'], 'quantity': 5}]
        }).json()

        client.post(f'/orders/{order["id"]}/cancel')

        # Spec'te açık değil, ama "OrderItem" kaldırılmazsa hala engeller
        resp = client.delete(f'/products/{prod["id"]}')
        assert resp.status_code == 409


class TestReports:
    """Report endpoint'leri."""

    def test_low_stock_report(self, client):
        """GET /reports/low-stock — stok düşük ürünler."""
        client.post('/products', json={
            'name': 'Widget1',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 5,
            'category': 'electronics'
        })
        client.post('/products', json={
            'name': 'Widget2',
            'sku': 'WID-002',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        })

        resp = client.get('/reports/low-stock?threshold=10')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['name'] == 'Widget1'

    def test_low_stock_report_default_threshold(self, client):
        """GET /reports/low-stock — varsayılan threshold=10."""
        client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 8,
            'category': 'electronics'
        })

        resp = client.get('/reports/low-stock')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

    def test_revenue_by_category(self, client):
        """GET /reports/revenue-by-category — kategoriye göre gelir."""
        prod1 = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        }).json()

        prod2 = client.post('/products', json={
            'name': 'Book',
            'sku': 'BOO-001',
            'price_cents': 500,
            'stock': 100,
            'category': 'books'
        }).json()

        # İki sipariş
        client.post('/orders', json={
            'items': [{'product_id': prod1['id'], 'quantity': 2}]
        })
        client.post('/orders', json={
            'items': [{'product_id': prod2['id'], 'quantity': 3}]
        })

        resp = client.get('/reports/revenue-by-category')
        assert resp.status_code == 200
        data = resp.json()
        assert data['electronics'] == 2000
        assert data['books'] == 1500

    def test_revenue_excludes_cancelled_orders(self, client):
        """GET /reports/revenue-by-category — iptal edilen siparişler hariç."""
        prod = client.post('/products', json={
            'name': 'Widget',
            'sku': 'WID-001',
            'price_cents': 1000,
            'stock': 100,
            'category': 'electronics'
        }).json()

        order = client.post('/orders', json={
            'items': [{'product_id': prod['id'], 'quantity': 5}]
        }).json()

        client.post(f'/orders/{order["id"]}/cancel')

        resp = client.get('/reports/revenue-by-category')
        assert resp.status_code == 200
        data = resp.json()
        assert 'electronics' not in data or data.get('electronics', 0) == 0
