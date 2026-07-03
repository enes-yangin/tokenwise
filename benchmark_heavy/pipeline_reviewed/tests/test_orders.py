"""Order endpoint testleri."""


def test_create_order_success(client):
    """Basit order oluşturma."""
    # Ürün oluştur
    prod_r = client.post("/products", json={
        "name": "Laptop", "sku": "LP1", "price_cents": 100000,
        "stock": 5, "category": "electronics"
    })
    assert prod_r.status_code == 201
    product_id = prod_r.json()["id"]

    # Order oluştur
    order_r = client.post("/orders", json={
        "items": [{"product_id": product_id, "quantity": 2}]
    })
    assert order_r.status_code == 201
    order = order_r.json()
    assert order["status"] == "pending"
    assert order["total_cents"] == 200000  # 100000 * 2
    assert len(order["items"]) == 1
    assert order["items"][0]["product_id"] == product_id
    assert order["items"][0]["quantity"] == 2
    assert order["items"][0]["unit_price_cents"] == 100000
    assert "created_at" in order


def test_create_order_multiple_items(client):
    """Multiple item'li order."""
    # Ürünler oluştur
    prod1_r = client.post("/products", json={
        "name": "Mouse", "sku": "M1", "price_cents": 5000,
        "stock": 10, "category": "accessories"
    })
    prod1_id = prod1_r.json()["id"]

    prod2_r = client.post("/products", json={
        "name": "Keyboard", "sku": "K1", "price_cents": 8000,
        "stock": 10, "category": "accessories"
    })
    prod2_id = prod2_r.json()["id"]

    # Multiple item order
    order_r = client.post("/orders", json={
        "items": [
            {"product_id": prod1_id, "quantity": 3},
            {"product_id": prod2_id, "quantity": 1},
        ]
    })
    assert order_r.status_code == 201
    order = order_r.json()
    assert order["total_cents"] == 5000 * 3 + 8000 * 1  # 23000
    assert len(order["items"]) == 2


def test_get_order(client):
    """Order getirme."""
    # Setup
    prod_r = client.post("/products", json={
        "name": "Monitor", "sku": "MO1", "price_cents": 25000,
        "stock": 3, "category": "electronics"
    })
    product_id = prod_r.json()["id"]

    order_r = client.post("/orders", json={
        "items": [{"product_id": product_id, "quantity": 1}]
    })
    order_id = order_r.json()["id"]

    # GET işlemi
    get_r = client.get(f"/orders/{order_id}")
    assert get_r.status_code == 200
    order = get_r.json()
    assert order["id"] == order_id
    assert order["status"] == "pending"
    assert order["total_cents"] == 25000


def test_get_order_not_found(client):
    """Mevcut olmayan order 404."""
    r = client.get("/orders/9999")
    assert r.status_code == 404


def test_create_order_product_not_found(client):
    """Mevcut olmayan ürünle order oluşturma hataları."""
    r = client.post("/orders", json={
        "items": [{"product_id": 9999, "quantity": 1}]
    })
    assert r.status_code == 404


def test_create_order_insufficient_stock(client):
    """Stok yetersiz hatası."""
    # Stok sınırlı ürün
    prod_r = client.post("/products", json={
        "name": "Rare Item", "sku": "RARE1", "price_cents": 10000,
        "stock": 2, "category": "misc"
    })
    product_id = prod_r.json()["id"]

    # Yeterli stok olmayan order
    r = client.post("/orders", json={
        "items": [{"product_id": product_id, "quantity": 5}]
    })
    assert r.status_code == 409


def test_create_order_reduces_stock(client):
    """Order oluşturma stoğu düşürür."""
    # Ürün: 10 stock
    prod_r = client.post("/products", json={
        "name": "Item", "sku": "I1", "price_cents": 1000,
        "stock": 10, "category": "misc"
    })
    product_id = prod_r.json()["id"]

    # 3 birim order
    client.post("/orders", json={
        "items": [{"product_id": product_id, "quantity": 3}]
    })

    # Kontrol: stok 7 olmalı
    prod_check = client.get(f"/products/{product_id}").json()
    assert prod_check["stock"] == 7


def test_cancel_order_success(client):
    """Order iptal etme."""
    # Setup
    prod_r = client.post("/products", json={
        "name": "Item", "sku": "CA1", "price_cents": 5000,
        "stock": 10, "category": "misc"
    })
    product_id = prod_r.json()["id"]

    order_r = client.post("/orders", json={
        "items": [{"product_id": product_id, "quantity": 4}]
    })
    order_id = order_r.json()["id"]

    # Kontrol: order pending, stok 6
    assert client.get(f"/orders/{order_id}").json()["status"] == "pending"
    assert client.get(f"/products/{product_id}").json()["stock"] == 6

    # İptal et
    cancel_r = client.post(f"/orders/{order_id}/cancel")
    assert cancel_r.status_code == 200
    cancel_order = cancel_r.json()
    assert cancel_order["status"] == "cancelled"

    # Kontrol: stok geri verilmiş (10 olmalı)
    prod_check = client.get(f"/products/{product_id}").json()
    assert prod_check["stock"] == 10


def test_cancel_order_already_cancelled(client):
    """Zaten iptal edilmiş order'ı iptal edemezsin."""
    # Setup
    prod_r = client.post("/products", json={
        "name": "Item", "sku": "CA2", "price_cents": 1000,
        "stock": 5, "category": "misc"
    })
    product_id = prod_r.json()["id"]

    order_r = client.post("/orders", json={
        "items": [{"product_id": product_id, "quantity": 1}]
    })
    order_id = order_r.json()["id"]

    # İlk iptal
    client.post(f"/orders/{order_id}/cancel")

    # İkinci iptal hatası
    r = client.post(f"/orders/{order_id}/cancel")
    assert r.status_code == 409


def test_cancel_order_multiple_items(client):
    """Multiple item'li order iptal edilince tüm stoklar geri verilir."""
    # İki ürün
    prod1_r = client.post("/products", json={
        "name": "P1", "sku": "MCA1", "price_cents": 1000,
        "stock": 10, "category": "misc"
    })
    prod1_id = prod1_r.json()["id"]

    prod2_r = client.post("/products", json={
        "name": "P2", "sku": "MCA2", "price_cents": 2000,
        "stock": 20, "category": "misc"
    })
    prod2_id = prod2_r.json()["id"]

    # Multiple item order
    order_r = client.post("/orders", json={
        "items": [
            {"product_id": prod1_id, "quantity": 3},
            {"product_id": prod2_id, "quantity": 5},
        ]
    })
    order_id = order_r.json()["id"]

    # Kontrol: stoklar düşmüş
    assert client.get(f"/products/{prod1_id}").json()["stock"] == 7
    assert client.get(f"/products/{prod2_id}").json()["stock"] == 15

    # İptal
    client.post(f"/orders/{order_id}/cancel")

    # Kontrol: stoklar geri verilmiş
    assert client.get(f"/products/{prod1_id}").json()["stock"] == 10
    assert client.get(f"/products/{prod2_id}").json()["stock"] == 20


def test_revenue_by_category_empty(client):
    """Hiç order yoksa boş report."""
    r = client.get("/reports/revenue-by-category")
    assert r.status_code == 200
    assert r.json() == {}


def test_revenue_by_category_single(client):
    """Tek kategori geliri."""
    # Ürün oluştur
    prod_r = client.post("/products", json={
        "name": "Book", "sku": "B1", "price_cents": 2000,
        "stock": 10, "category": "books"
    })
    product_id = prod_r.json()["id"]

    # Order oluştur
    client.post("/orders", json={
        "items": [{"product_id": product_id, "quantity": 3}]
    })

    # Report
    report_r = client.get("/reports/revenue-by-category")
    assert report_r.status_code == 200
    report = report_r.json()
    assert report["books"] == 6000  # 2000 * 3


def test_revenue_by_category_multiple_categories(client):
    """Birden çok kategori geliri."""
    # İki kategoriden ürünler
    prod1_r = client.post("/products", json={
        "name": "Book", "sku": "B2", "price_cents": 1500,
        "stock": 10, "category": "books"
    })
    prod1_id = prod1_r.json()["id"]

    prod2_r = client.post("/products", json={
        "name": "Pen", "sku": "P1", "price_cents": 500,
        "stock": 20, "category": "stationery"
    })
    prod2_id = prod2_r.json()["id"]

    # İki order
    client.post("/orders", json={
        "items": [{"product_id": prod1_id, "quantity": 2}]
    })
    client.post("/orders", json={
        "items": [{"product_id": prod2_id, "quantity": 4}]
    })

    # Report
    report_r = client.get("/reports/revenue-by-category")
    report = report_r.json()
    assert report["books"] == 3000  # 1500 * 2
    assert report["stationery"] == 2000  # 500 * 4


def test_revenue_by_category_cancelled_excluded(client):
    """İptal edilmiş order'lar raporda sayılmaz."""
    # Ürün
    prod_r = client.post("/products", json={
        "name": "Item", "sku": "RC1", "price_cents": 1000,
        "stock": 10, "category": "cat"
    })
    product_id = prod_r.json()["id"]

    # Order oluştur ve iptal et
    order_r = client.post("/orders", json={
        "items": [{"product_id": product_id, "quantity": 5}]
    })
    order_id = order_r.json()["id"]
    client.post(f"/orders/{order_id}/cancel")

    # Report: boş olmalı (cancelled order sayılmaz)
    report_r = client.get("/reports/revenue-by-category")
    report = report_r.json()
    assert report == {}


def test_create_order_atomic_no_partial_stock_change(client):
    """Çok kalemli siparişte bir kalem yetersizse HİÇBİR stok değişmez (atomik)."""
    p1 = client.post("/products", json={
        "name": "A", "sku": "AT1", "price_cents": 1000, "stock": 10, "category": "m"
    }).json()
    p2 = client.post("/products", json={
        "name": "B", "sku": "AT2", "price_cents": 1000, "stock": 1, "category": "m"
    }).json()

    r = client.post("/orders", json={"items": [
        {"product_id": p1["id"], "quantity": 5},
        {"product_id": p2["id"], "quantity": 5},  # yetersiz
    ]})
    assert r.status_code == 409
    # İlk kalemin stoğu düşmemiş olmalı
    assert client.get(f"/products/{p1['id']}").json()["stock"] == 10
    assert client.get(f"/products/{p2['id']}").json()["stock"] == 1


def test_create_order_duplicate_lines_aggregated(client):
    """Aynı ürün çoklu satırda → miktarlar toplanarak stok kontrol edilir."""
    p = client.post("/products", json={
        "name": "A", "sku": "DUP1", "price_cents": 1000, "stock": 5, "category": "m"
    }).json()
    # 3 + 3 = 6 > 5 → 409, stok değişmez
    r = client.post("/orders", json={"items": [
        {"product_id": p["id"], "quantity": 3},
        {"product_id": p["id"], "quantity": 3},
    ]})
    assert r.status_code == 409
    assert client.get(f"/products/{p['id']}").json()["stock"] == 5

    # 2 + 2 = 4 <= 5 → başarılı, toplam 4 düşer
    r2 = client.post("/orders", json={"items": [
        {"product_id": p["id"], "quantity": 2},
        {"product_id": p["id"], "quantity": 2},
    ]})
    assert r2.status_code == 201
    assert client.get(f"/products/{p['id']}").json()["stock"] == 1


def test_double_cancel_does_not_double_restore_stock(client):
    """İkinci iptal 409 ve stok iki kat geri yüklenmez."""
    p = client.post("/products", json={
        "name": "A", "sku": "DC1", "price_cents": 1000, "stock": 10, "category": "m"
    }).json()
    order_id = client.post("/orders", json={
        "items": [{"product_id": p["id"], "quantity": 4}]
    }).json()["id"]

    assert client.post(f"/orders/{order_id}/cancel").status_code == 200
    assert client.get(f"/products/{p['id']}").json()["stock"] == 10
    assert client.post(f"/orders/{order_id}/cancel").status_code == 409
    assert client.get(f"/products/{p['id']}").json()["stock"] == 10  # 14 değil


def test_price_snapshot_frozen_on_order(client):
    """Sipariş sonrası ürün fiyatı değişse geçmiş order total'i değişmez."""
    p = client.post("/products", json={
        "name": "A", "sku": "PS1", "price_cents": 1000, "stock": 10, "category": "m"
    }).json()
    order_id = client.post("/orders", json={
        "items": [{"product_id": p["id"], "quantity": 2}]
    }).json()["id"]

    client.patch(f"/products/{p['id']}", json={"price_cents": 9999})
    order = client.get(f"/orders/{order_id}").json()
    assert order["total_cents"] == 2000
    assert order["items"][0]["unit_price_cents"] == 1000


def test_delete_referenced_product_conflict(client):
    """order_items'ta referanslı ürün DELETE edilmek istenirse 409."""
    p = client.post("/products", json={
        "name": "A", "sku": "REF1", "price_cents": 1000, "stock": 10, "category": "m"
    }).json()
    client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 1}]})

    r = client.delete(f"/products/{p['id']}")
    assert r.status_code == 409
    # Hala mevcut
    assert client.get(f"/products/{p['id']}").status_code == 200


def test_create_order_no_items(client):
    """Empty items array hatası."""
    r = client.post("/orders", json={"items": []})
    assert r.status_code == 422


def test_create_order_invalid_quantity(client):
    """Negatif quantity hatası."""
    # Ürün oluştur
    prod_r = client.post("/products", json={
        "name": "Item", "sku": "IQ1", "price_cents": 1000,
        "stock": 10, "category": "misc"
    })
    product_id = prod_r.json()["id"]

    r = client.post("/orders", json={
        "items": [{"product_id": product_id, "quantity": -1}]
    })
    assert r.status_code == 422


def test_create_order_zero_quantity(client):
    """Zero quantity hatası."""
    # Ürün oluştur
    prod_r = client.post("/products", json={
        "name": "Item", "sku": "ZQ1", "price_cents": 1000,
        "stock": 10, "category": "misc"
    })
    product_id = prod_r.json()["id"]

    r = client.post("/orders", json={
        "items": [{"product_id": product_id, "quantity": 0}]
    })
    assert r.status_code == 422
