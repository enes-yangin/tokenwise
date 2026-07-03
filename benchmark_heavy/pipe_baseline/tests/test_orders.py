"""Order endpoint testleri."""


def test_create_order_success(client):
    # Ürün oluştur
    product = client.post("/products", json={
        "name": "Widget", "sku": "W1", "price_cents": 500,
        "stock": 10, "category": "tools"
    }).json()

    # Sipariş oluştur
    r = client.post("/orders", json={
        "items": [{"product_id": product["id"], "quantity": 2}]
    })
    assert r.status_code == 201
    order = r.json()
    assert order["status"] == "pending"
    assert order["total_cents"] == 1000  # 500 * 2
    assert len(order["items"]) == 1
    assert order["items"][0]["product_id"] == product["id"]
    assert order["items"][0]["quantity"] == 2
    assert order["items"][0]["unit_price_cents"] == 500

    # Stoğun düştüğünü kontrol et
    updated_product = client.get(f"/products/{product['id']}").json()
    assert updated_product["stock"] == 8  # 10 - 2


def test_get_order(client):
    product = client.post("/products", json={
        "name": "Widget", "sku": "W1", "price_cents": 500,
        "stock": 10, "category": "tools"
    }).json()

    r = client.post("/orders", json={
        "items": [{"product_id": product["id"], "quantity": 1}]
    })
    order_id = r.json()["id"]

    # GET işlemi
    order = client.get(f"/orders/{order_id}").json()
    assert order["id"] == order_id
    assert order["status"] == "pending"
    assert order["total_cents"] == 500


def test_get_order_not_found(client):
    r = client.get("/orders/999")
    assert r.status_code == 404


def test_create_order_product_not_found(client):
    r = client.post("/orders", json={
        "items": [{"product_id": 999, "quantity": 1}]
    })
    assert r.status_code == 404


def test_create_order_insufficient_stock(client):
    product = client.post("/products", json={
        "name": "Widget", "sku": "W1", "price_cents": 500,
        "stock": 1, "category": "tools"
    }).json()

    r = client.post("/orders", json={
        "items": [{"product_id": product["id"], "quantity": 5}]
    })
    assert r.status_code == 409


def test_cancel_order(client):
    product = client.post("/products", json={
        "name": "Widget", "sku": "W1", "price_cents": 500,
        "stock": 10, "category": "tools"
    }).json()

    # Sipariş oluştur
    r = client.post("/orders", json={
        "items": [{"product_id": product["id"], "quantity": 2}]
    })
    order_id = r.json()["id"]

    # Stoğun düştüğünü kontrol et
    assert client.get(f"/products/{product['id']}").json()["stock"] == 8

    # Siparişi iptal et
    r = client.post(f"/orders/{order_id}/cancel")
    assert r.status_code == 200
    order = r.json()
    assert order["status"] == "cancelled"

    # Stoğun geri yüklendiğini kontrol et
    assert client.get(f"/products/{product['id']}").json()["stock"] == 10


def test_cancel_order_not_found(client):
    r = client.post("/orders/999/cancel")
    assert r.status_code == 404


def test_cancel_already_cancelled(client):
    product = client.post("/products", json={
        "name": "Widget", "sku": "W1", "price_cents": 500,
        "stock": 10, "category": "tools"
    }).json()

    r = client.post("/orders", json={
        "items": [{"product_id": product["id"], "quantity": 1}]
    })
    order_id = r.json()["id"]

    # İlk iptal
    assert client.post(f"/orders/{order_id}/cancel").status_code == 200

    # İkinci iptal — hata
    r = client.post(f"/orders/{order_id}/cancel")
    assert r.status_code == 409


def test_revenue_by_category(client):
    # Ürünler oluştur
    p1 = client.post("/products", json={
        "name": "P1", "sku": "P1", "price_cents": 1000,
        "stock": 100, "category": "electronics"
    }).json()

    p2 = client.post("/products", json={
        "name": "P2", "sku": "P2", "price_cents": 500,
        "stock": 100, "category": "tools"
    }).json()

    # Siparişler oluştur
    client.post("/orders", json={
        "items": [{"product_id": p1["id"], "quantity": 2}]  # 2000
    })
    client.post("/orders", json={
        "items": [{"product_id": p2["id"], "quantity": 3}]  # 1500
    })
    client.post("/orders", json={
        "items": [{"product_id": p1["id"], "quantity": 1}]  # 1000
    })

    r = client.get("/reports/revenue-by-category")
    assert r.status_code == 200
    revenue = r.json()
    assert revenue["electronics"] == 3000  # 2000 + 1000
    assert revenue["tools"] == 1500


def test_create_order_multiple_items(client):
    p1 = client.post("/products", json={
        "name": "P1", "sku": "P1", "price_cents": 1000,
        "stock": 100, "category": "electronics"
    }).json()

    p2 = client.post("/products", json={
        "name": "P2", "sku": "P2", "price_cents": 500,
        "stock": 100, "category": "tools"
    }).json()

    r = client.post("/orders", json={
        "items": [
            {"product_id": p1["id"], "quantity": 2},
            {"product_id": p2["id"], "quantity": 3}
        ]
    })
    assert r.status_code == 201
    order = r.json()
    assert order["total_cents"] == 3500  # 2*1000 + 3*500
    assert len(order["items"]) == 2

    # Stoğu kontrol et
    assert client.get(f"/products/{p1['id']}").json()["stock"] == 98
    assert client.get(f"/products/{p2['id']}").json()["stock"] == 97
