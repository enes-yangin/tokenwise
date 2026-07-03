"""Order endpoint testleri."""


def make_product(client, **overrides):
    body = {
        "name": "Widget", "sku": "SKU1", "price_cents": 500,
        "stock": 10, "category": "tools",
    }
    body.update(overrides)
    r = client.post("/products", json=body)
    assert r.status_code == 201
    return r.json()


def test_create_order_snapshots_price_and_reduces_stock(client):
    p = make_product(client, sku="A1", price_cents=300, stock=10)
    r = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 2}]})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    assert body["items"] == [
        {"product_id": p["id"], "quantity": 2, "unit_price_cents": 300}
    ]
    assert body["total_cents"] == 600
    assert client.get(f"/products/{p['id']}").json()["stock"] == 8


def test_atomic_stock_reduction_no_partial_and_sums_duplicate_lines(client):
    p1 = make_product(client, sku="A2", price_cents=100, stock=5)
    p2 = make_product(client, sku="A3", price_cents=100, stock=1)
    # same product referenced twice -> combined qty (3+3=6) also exceeds stock for p1 check;
    # use p2 to force insufficient stock while p1 has enough for a partial write test
    r = client.post("/orders", json={
        "items": [
            {"product_id": p1["id"], "quantity": 3},
            {"product_id": p2["id"], "quantity": 2},  # p2 stock=1 -> insufficient
        ]
    })
    assert r.status_code == 409
    # no partial deduction: p1 stock must remain untouched
    assert client.get(f"/products/{p1['id']}").json()["stock"] == 5
    assert client.get(f"/products/{p2['id']}").json()["stock"] == 1


def test_duplicate_product_lines_sum_quantity_against_stock(client):
    p = make_product(client, sku="A4", price_cents=100, stock=5)
    r = client.post("/orders", json={
        "items": [
            {"product_id": p["id"], "quantity": 3},
            {"product_id": p["id"], "quantity": 3},
        ]
    })
    assert r.status_code == 409
    assert client.get(f"/products/{p['id']}").json()["stock"] == 5

    r2 = client.post("/orders", json={
        "items": [
            {"product_id": p["id"], "quantity": 2},
            {"product_id": p["id"], "quantity": 3},
        ]
    })
    assert r2.status_code == 201
    assert client.get(f"/products/{p['id']}").json()["stock"] == 0


def test_price_snapshot_unaffected_by_later_patch(client):
    p = make_product(client, sku="A5", price_cents=200, stock=5)
    r = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 2}]})
    order = r.json()
    client.patch(f"/products/{p['id']}", json={"price_cents": 999})
    got = client.get(f"/orders/{order['id']}").json()
    assert got["total_cents"] == 400
    assert got["items"][0]["unit_price_cents"] == 200


def test_cancel_restores_stock_and_is_idempotent(client):
    p = make_product(client, sku="A6", price_cents=100, stock=5)
    order = client.post(
        "/orders", json={"items": [{"product_id": p["id"], "quantity": 2}]}
    ).json()
    assert client.get(f"/products/{p['id']}").json()["stock"] == 3

    r1 = client.post(f"/orders/{order['id']}/cancel")
    assert r1.status_code == 200
    assert r1.json()["status"] == "cancelled"
    assert client.get(f"/products/{p['id']}").json()["stock"] == 5

    r2 = client.post(f"/orders/{order['id']}/cancel")
    assert r2.status_code == 409
    assert client.get(f"/products/{p['id']}").json()["stock"] == 5


def test_money_is_int_cents_no_float(client):
    p = make_product(client, sku="A7", price_cents=333, stock=5)
    r = client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 3}]})
    body = r.json()
    assert isinstance(body["total_cents"], int)
    assert body["total_cents"] == 999
    assert isinstance(body["items"][0]["unit_price_cents"], int)


def test_product_referenced_by_order_cannot_be_deleted(client):
    p = make_product(client, sku="A8", price_cents=100, stock=5)
    client.post("/orders", json={"items": [{"product_id": p["id"], "quantity": 1}]})
    r = client.delete(f"/products/{p['id']}")
    assert r.status_code == 409


def test_validation_quantity_and_empty_items_422(client):
    p = make_product(client, sku="A9", price_cents=100, stock=5)
    assert client.post(
        "/orders", json={"items": [{"product_id": p["id"], "quantity": 0}]}
    ).status_code == 422
    assert client.post(
        "/orders", json={"items": [{"product_id": p["id"], "quantity": -1}]}
    ).status_code == 422
    assert client.post("/orders", json={"items": []}).status_code == 422


def test_404_for_missing_order_and_product(client):
    assert client.get("/orders/999999").status_code == 404
    assert client.post("/orders/999999/cancel").status_code == 404
    assert client.post(
        "/orders", json={"items": [{"product_id": 999999, "quantity": 1}]}
    ).status_code == 404


def test_revenue_by_category_excludes_cancelled(client):
    p1 = make_product(client, sku="B1", price_cents=100, stock=10, category="cat-a")
    p2 = make_product(client, sku="B2", price_cents=250, stock=10, category="cat-b")

    client.post("/orders", json={"items": [{"product_id": p1["id"], "quantity": 2}]})
    order2 = client.post(
        "/orders", json={"items": [{"product_id": p2["id"], "quantity": 1}]}
    ).json()
    client.post(f"/orders/{order2['id']}/cancel")

    report = client.get("/reports/revenue-by-category").json()
    assert report.get("cat-a") == 200
    assert "cat-b" not in report
