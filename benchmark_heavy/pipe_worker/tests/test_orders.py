"""Order endpoint testleri."""


def test_happy_path_create_order(client):
    """Mutlu yol: ürün oluştur (stock=10, price=500), sipariş qty=2 → 201."""
    # Ürün oluştur
    p = client.post("/products", json={
        "name": "Widget", "sku": "W1", "price_cents": 500,
        "stock": 10, "category": "tools"}).json()
    pid = p["id"]

    # Sipariş oluştur
    r = client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": 2}]
    })
    assert r.status_code == 201
    order = r.json()

    # Yanıt şekli doğru
    assert order["status"] == "active"
    assert len(order["items"]) == 1
    assert order["items"][0]["product_id"] == pid
    assert order["items"][0]["quantity"] == 2
    assert order["items"][0]["unit_price_cents"] == 500
    assert order["total_cents"] == 1000

    # Ürün stoğu düşmüş
    p = client.get(f"/products/{pid}").json()
    assert p["stock"] == 8


def test_404_product_not_found(client):
    """404 ürün yok."""
    r = client.post("/orders", json={
        "items": [{"product_id": 999, "quantity": 1}]
    })
    assert r.status_code == 404
    assert r.json()["detail"] == "product not found"


def test_409_insufficient_stock_single_item(client):
    """409 yetersiz stok (tek kalem): stock=1, qty=5."""
    p = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 1, "category": "c"}).json()
    pid = p["id"]

    r = client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": 5}]
    })
    assert r.status_code == 409
    assert r.json()["detail"] == "insufficient stock"

    # Stok değişmemiş
    assert client.get(f"/products/{pid}").json()["stock"] == 1


def test_409_multi_item_one_fails_all_rollback(client):
    """409 çok kalemli, tek kalem yetersiz → tümü reddedilir."""
    pA = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 10, "category": "c"}).json()
    pB = client.post("/products", json={
        "name": "B", "sku": "B1", "price_cents": 200,
        "stock": 0, "category": "c"}).json()

    r = client.post("/orders", json={
        "items": [
            {"product_id": pA["id"], "quantity": 5},
            {"product_id": pB["id"], "quantity": 1}
        ]
    })
    assert r.status_code == 409
    assert r.json()["detail"] == "insufficient stock"

    # A'nın stoğu düşmemiş (rollback)
    assert client.get(f"/products/{pA['id']}").json()["stock"] == 10


def test_duplicate_product_id_merge(client):
    """Aynı ürün iki satırda birleşir: qty 1 + 2 → qty 3."""
    p = client.post("/products", json={
        "name": "C", "sku": "C1", "price_cents": 300,
        "stock": 10, "category": "c"}).json()
    pid = p["id"]

    r = client.post("/orders", json={
        "items": [
            {"product_id": pid, "quantity": 1},
            {"product_id": pid, "quantity": 2}
        ]
    })
    assert r.status_code == 201
    order = r.json()

    # Tek kalem, toplam qty=3
    assert len(order["items"]) == 1
    assert order["items"][0]["quantity"] == 3
    assert order["total_cents"] == 900

    # Stok 3 düşmüş
    assert client.get(f"/products/{pid}").json()["stock"] == 7


def test_price_snapshot(client):
    """Fiyat snapshot: sipariş sonrası ürün fiyatını değiştir → order hâlâ eski fiyat döner."""
    p = client.post("/products", json={
        "name": "D", "sku": "D1", "price_cents": 500,
        "stock": 10, "category": "c"}).json()
    pid = p["id"]

    # Sipariş oluştur (fiyat snapshot = 500)
    order = client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": 2}]
    }).json()
    order_id = order["id"]

    assert order["items"][0]["unit_price_cents"] == 500
    assert order["total_cents"] == 1000

    # Ürün fiyatını değiştir
    client.patch(f"/products/{pid}", json={"price_cents": 1000})

    # Order hâlâ eski fiyat döner
    order = client.get(f"/orders/{order_id}").json()
    assert order["items"][0]["unit_price_cents"] == 500
    assert order["total_cents"] == 1000


def test_cancel_order_restore_stock(client):
    """İptal + stok iadesi: sipariş → cancel → status="cancelled", stok iade."""
    p = client.post("/products", json={
        "name": "E", "sku": "E1", "price_cents": 100,
        "stock": 10, "category": "c"}).json()
    pid = p["id"]

    # Sipariş oluştur
    order = client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": 3}]
    }).json()
    order_id = order["id"]
    assert client.get(f"/products/{pid}").json()["stock"] == 7

    # İptal et
    r = client.post(f"/orders/{order_id}/cancel")
    assert r.status_code == 200
    order = r.json()
    assert order["status"] == "cancelled"

    # Stok iade edilmiş
    assert client.get(f"/products/{pid}").json()["stock"] == 10


def test_cancel_idempotency(client):
    """İptal idempotency: iki kez cancel → ikisi de 200, stok yalnızca BİR kez iade."""
    p = client.post("/products", json={
        "name": "F", "sku": "F1", "price_cents": 100,
        "stock": 10, "category": "c"}).json()
    pid = p["id"]

    order = client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": 2}]
    }).json()
    order_id = order["id"]

    # İlk cancel
    r1 = client.post(f"/orders/{order_id}/cancel")
    assert r1.status_code == 200
    stock_after_first = client.get(f"/products/{pid}").json()["stock"]

    # İkinci cancel
    r2 = client.post(f"/orders/{order_id}/cancel")
    assert r2.status_code == 200
    stock_after_second = client.get(f"/products/{pid}").json()["stock"]

    # Stok değişmediği (çift iade yok)
    assert stock_after_first == stock_after_second == 10


def test_422_empty_items(client):
    """422 validasyon: boş items."""
    r = client.post("/orders", json={"items": []})
    assert r.status_code == 422


def test_422_zero_quantity(client):
    """422 validasyon: quantity=0."""
    p = client.post("/products", json={
        "name": "G", "sku": "G1", "price_cents": 100,
        "stock": 10, "category": "c"}).json()
    pid = p["id"]

    r = client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": 0}]
    })
    assert r.status_code == 422


def test_revenue_by_category(client):
    """Revenue raporu: iki kategoride active siparişler + bir iptal → active only."""
    # Kategori "cat1": ürün A (price=100)
    pA = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 10, "category": "cat1"}).json()

    # Kategori "cat2": ürün B (price=200)
    pB = client.post("/products", json={
        "name": "B", "sku": "B1", "price_cents": 200,
        "stock": 10, "category": "cat2"}).json()

    # Active sipariş: A qty=2 (200), B qty=1 (200)
    order1 = client.post("/orders", json={
        "items": [
            {"product_id": pA["id"], "quantity": 2},
            {"product_id": pB["id"], "quantity": 1}
        ]
    }).json()

    # Active sipariş: A qty=1 (100)
    order2 = client.post("/orders", json={
        "items": [{"product_id": pA["id"], "quantity": 1}]
    }).json()

    # İptal edilmiş sipariş: B qty=5 (1000)
    order3 = client.post("/orders", json={
        "items": [{"product_id": pB["id"], "quantity": 5}]
    }).json()
    client.post(f"/orders/{order3['id']}/cancel")

    # Rapor
    r = client.get("/reports/revenue-by-category")
    assert r.status_code == 200
    revenue = r.json()

    # cat1: 200 + 100 = 300
    # cat2: 200 (iptal edilmiş 1000 dahil değil)
    assert revenue["cat1"] == 300
    assert revenue["cat2"] == 200


def test_deleted_product_snapshot(client):
    """Silinmiş ürün / snapshot: sipariş ver, ürünü sil, GET order snapshot'ı korur."""
    p = client.post("/products", json={
        "name": "H", "sku": "H1", "price_cents": 500,
        "stock": 10, "category": "c"}).json()
    pid = p["id"]

    # Sipariş oluştur
    order = client.post("/orders", json={
        "items": [{"product_id": pid, "quantity": 2}]
    }).json()
    order_id = order["id"]

    assert order["total_cents"] == 1000

    # Ürünü sil
    client.delete(f"/products/{pid}")

    # Order hâlâ snapshot'ı korur
    order = client.get(f"/orders/{order_id}").json()
    assert order["items"][0]["product_id"] == pid
    assert order["items"][0]["unit_price_cents"] == 500
    assert order["total_cents"] == 1000
