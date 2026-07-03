"""Order endpoint testleri."""


def _make_product(client, sku="P1", price_cents=1000, stock=10, category="cat1"):
    r = client.post("/products", json={
        "name": "Prod", "sku": sku, "price_cents": price_cents,
        "stock": stock, "category": category})
    assert r.status_code == 201
    return r.json()


def test_create_order_snapshots_price_and_reduces_stock(client):
    p = _make_product(client, sku="A1", price_cents=500, stock=10)
    r = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 3}]})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    assert body["items"] == [
        {"product_id": p["id"], "quantity": 3, "unit_price_cents": 500}
    ]
    assert body["total_cents"] == 1500

    remaining = client.get(f"/products/{p['id']}").json()
    assert remaining["stock"] == 7


def test_atomic_stock_reduction_no_partial_and_aggregates_same_product(client):
    p1 = _make_product(client, sku="B1", stock=5)
    p2 = _make_product(client, sku="B2", stock=1)

    # Aynı ürün birden fazla satırda -> toplam miktar kontrolü (5 <= stock=5 tek satırda olsaydı geçerdi,
    # ama iki satır toplamı stock'u aşıyor: 3+3=6 > 5)
    r = client.post("/orders", json={
        "items": [
            {"product_id": p1["id"], "quantity": 3},
            {"product_id": p1["id"], "quantity": 3},
            {"product_id": p2["id"], "quantity": 1},
        ]
    })
    assert r.status_code == 409

    # Kısmi düşüm olmamalı: p1 ve p2 stokları değişmemiş olmalı.
    assert client.get(f"/products/{p1['id']}").json()["stock"] == 5
    assert client.get(f"/products/{p2['id']}").json()["stock"] == 1


def test_aggregated_same_product_quantity_success(client):
    p = _make_product(client, sku="C1", stock=10, price_cents=200)
    r = client.post("/orders", json={
        "items": [
            {"product_id": p["id"], "quantity": 4},
            {"product_id": p["id"], "quantity": 4},
        ]
    })
    assert r.status_code == 201
    body = r.json()
    assert body["total_cents"] == 1600
    assert client.get(f"/products/{p['id']}").json()["stock"] == 2


def test_insufficient_stock_409(client):
    p = _make_product(client, sku="D1", stock=2)
    r = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 3}]})
    assert r.status_code == 409
    assert client.get(f"/products/{p['id']}").json()["stock"] == 2


def test_missing_product_404(client):
    r = client.post("/orders", json={"items": [{"product_id": 9999, "quantity": 1}]})
    assert r.status_code == 404


def test_validation_errors_422(client):
    p = _make_product(client, sku="E1")
    r = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 0}]})
    assert r.status_code == 422

    r = client.post("/orders", json={"items": []})
    assert r.status_code == 422


def test_price_snapshot_unaffected_by_later_price_change(client):
    p = _make_product(client, sku="F1", price_cents=1000, stock=10)
    r = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 2}]})
    order_id = r.json()["id"]
    assert r.json()["total_cents"] == 2000

    patch = client.patch(f"/products/{p['id']}", json={"price_cents": 5000})
    assert patch.status_code == 200

    order = client.get(f"/orders/{order_id}").json()
    assert order["total_cents"] == 2000
    assert order["items"][0]["unit_price_cents"] == 1000


def test_get_order_404(client):
    assert client.get("/orders/9999").status_code == 404


def test_cancel_order_restores_stock_and_is_idempotent(client):
    p = _make_product(client, sku="G1", stock=10)
    r = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 4}]})
    order_id = r.json()["id"]
    assert client.get(f"/products/{p['id']}").json()["stock"] == 6

    cancel1 = client.post(f"/orders/{order_id}/cancel")
    assert cancel1.status_code == 200
    assert cancel1.json()["status"] == "cancelled"
    assert client.get(f"/products/{p['id']}").json()["stock"] == 10

    cancel2 = client.post(f"/orders/{order_id}/cancel")
    assert cancel2.status_code == 409
    # Stok tekrar yüklenmemeli.
    assert client.get(f"/products/{p['id']}").json()["stock"] == 10


def test_cancel_missing_order_404(client):
    assert client.post("/orders/9999/cancel").status_code == 404


def test_delete_referenced_product_returns_409(client):
    p = _make_product(client, sku="H1", stock=5)
    client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 1}]})
    r = client.delete(f"/products/{p['id']}")
    assert r.status_code == 409


def test_delete_unreferenced_product_still_works(client):
    p = _make_product(client, sku="I1", stock=5)
    r = client.delete(f"/products/{p['id']}")
    assert r.status_code == 204


def test_revenue_by_category_excludes_cancelled(client):
    p1 = _make_product(client, sku="J1", price_cents=1000, stock=10, category="books")
    p2 = _make_product(client, sku="J2", price_cents=500, stock=10, category="toys")

    r1 = client.post("/orders", json={"items": [{"product_id": p1["id"], "quantity": 2}]})
    r2 = client.post("/orders", json={"items": [{"product_id": p2["id"], "quantity": 3}]})
    order2_id = r2.json()["id"]

    client.post(f"/orders/{order2_id}/cancel")

    report = client.get("/reports/revenue-by-category").json()
    assert report == {"books": 2000}


def test_money_is_int_cents_no_float(client):
    p = _make_product(client, sku="K1", price_cents=333, stock=10)
    r = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 3}]})
    body = r.json()
    assert isinstance(body["total_cents"], int)
    assert body["total_cents"] == 999
    for item in body["items"]:
        assert isinstance(item["unit_price_cents"], int)
