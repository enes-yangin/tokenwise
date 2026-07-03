"""Order endpoint testleri — eksiksiz edge case'ler."""


def test_create_order_basic(client):
    """Test basic order creation with single item."""
    # Create product
    prod_r = client.post("/products", json={
        "name": "Widget", "sku": "W1", "price_cents": 500,
        "stock": 10, "category": "tools"})
    prod_id = prod_r.json()["id"]

    # Create order
    r = client.post("/orders", json={
        "items": [{"product_id": prod_id, "quantity": 3}]})
    assert r.status_code == 201
    order = r.json()
    assert order["status"] == "pending"
    assert order["total_cents"] == 1500  # 3 * 500
    assert len(order["items"]) == 1
    assert order["items"][0]["product_id"] == prod_id
    assert order["items"][0]["quantity"] == 3
    assert order["items"][0]["unit_price_cents"] == 500


def test_create_order_multiple_items(client):
    """Test order with multiple different products."""
    # Create products
    p1 = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 10, "category": "cat1"}).json()["id"]
    p2 = client.post("/products", json={
        "name": "B", "sku": "B1", "price_cents": 200,
        "stock": 20, "category": "cat2"}).json()["id"]

    # Create order
    r = client.post("/orders", json={
        "items": [
            {"product_id": p1, "quantity": 2},
            {"product_id": p2, "quantity": 3}
        ]})
    assert r.status_code == 201
    order = r.json()
    assert order["total_cents"] == 200 + 600  # 2*100 + 3*200
    assert len(order["items"]) == 2


def test_create_order_same_product_multiple_lines(client):
    """Test aggregation of same product across multiple lines."""
    p = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 10, "category": "cat1"}).json()["id"]

    # Create order with same product twice
    r = client.post("/orders", json={
        "items": [
            {"product_id": p, "quantity": 3},
            {"product_id": p, "quantity": 4}
        ]})
    assert r.status_code == 201
    order = r.json()
    # Total quantity should be 7, but since they're separate lines in the items array:
    assert len(order["items"]) == 2
    assert order["items"][0]["quantity"] == 3
    assert order["items"][1]["quantity"] == 4
    # Product stock should have decreased by 7 total
    prod = client.get(f"/products/{p}").json()
    assert prod["stock"] == 3  # 10 - 7


def test_stock_decreased_after_order(client):
    """Test that product stock is properly decreased after order."""
    p = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 10, "category": "cat1"}).json()["id"]

    client.post("/orders", json={"items": [{"product_id": p, "quantity": 3}]})
    prod = client.get(f"/products/{p}").json()
    assert prod["stock"] == 7


def test_insufficient_stock_409(client):
    """Test that insufficient stock returns 409."""
    p = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 5, "category": "cat1"}).json()["id"]

    r = client.post("/orders", json={
        "items": [{"product_id": p, "quantity": 10}]})
    assert r.status_code == 409


def test_insufficient_stock_partial_aggregation(client):
    """Test insufficient stock check with aggregation of same product."""
    p = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 5, "category": "cat1"}).json()["id"]

    # Total 7 units requested but only 5 available
    r = client.post("/orders", json={
        "items": [
            {"product_id": p, "quantity": 3},
            {"product_id": p, "quantity": 4}
        ]})
    assert r.status_code == 409
    # Stock should not change (atomicity)
    prod = client.get(f"/products/{p}").json()
    assert prod["stock"] == 5


def test_nonexistent_product_404(client):
    """Test that order with non-existent product returns 404."""
    r = client.post("/orders", json={
        "items": [{"product_id": 9999, "quantity": 1}]})
    assert r.status_code == 404


def test_zero_quantity_422(client):
    """Test that zero quantity returns 422."""
    p = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 10, "category": "cat1"}).json()["id"]

    r = client.post("/orders", json={
        "items": [{"product_id": p, "quantity": 0}]})
    assert r.status_code == 422


def test_negative_quantity_422(client):
    """Test that negative quantity returns 422."""
    p = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 10, "category": "cat1"}).json()["id"]

    r = client.post("/orders", json={
        "items": [{"product_id": p, "quantity": -5}]})
    assert r.status_code == 422


def test_empty_items_422(client):
    """Test that empty items array returns 422."""
    r = client.post("/orders", json={"items": []})
    assert r.status_code == 422


def test_get_order(client):
    """Test GET /orders/{id}."""
    p = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 10, "category": "cat1"}).json()["id"]

    created = client.post("/orders", json={
        "items": [{"product_id": p, "quantity": 3}]}).json()
    order_id = created["id"]

    r = client.get(f"/orders/{order_id}")
    assert r.status_code == 200
    order = r.json()
    assert order["id"] == order_id
    assert order["status"] == "pending"


def test_get_nonexistent_order_404(client):
    """Test GET /orders/{id} with non-existent order."""
    r = client.get("/orders/9999")
    assert r.status_code == 404


def test_cancel_order(client):
    """Test POST /orders/{id}/cancel."""
    p = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 10, "category": "cat1"}).json()["id"]

    created = client.post("/orders", json={
        "items": [{"product_id": p, "quantity": 3}]}).json()
    order_id = created["id"]

    # Check stock decreased
    assert client.get(f"/products/{p}").json()["stock"] == 7

    # Cancel order
    r = client.post(f"/orders/{order_id}/cancel")
    assert r.status_code == 200
    order = r.json()
    assert order["status"] == "cancelled"

    # Check stock restored
    assert client.get(f"/products/{p}").json()["stock"] == 10


def test_cancel_nonexistent_order_404(client):
    """Test cancel with non-existent order."""
    r = client.post("/orders/9999/cancel")
    assert r.status_code == 404


def test_cancel_already_cancelled_409(client):
    """Test idempotency: cancelling already cancelled order returns 409."""
    p = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 10, "category": "cat1"}).json()["id"]

    created = client.post("/orders", json={
        "items": [{"product_id": p, "quantity": 3}]}).json()
    order_id = created["id"]

    # First cancel
    r1 = client.post(f"/orders/{order_id}/cancel")
    assert r1.status_code == 200

    # Second cancel should fail
    r2 = client.post(f"/orders/{order_id}/cancel")
    assert r2.status_code == 409

    # Stock should still be correct (restored only once)
    assert client.get(f"/products/{p}").json()["stock"] == 10


def test_price_snapshot(client):
    """Test that order captures price snapshot at order time."""
    p = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 10, "category": "cat1"}).json()["id"]

    # Create order at price 100
    created = client.post("/orders", json={
        "items": [{"product_id": p, "quantity": 2}]}).json()
    assert created["total_cents"] == 200

    # Change product price
    client.patch(f"/products/{p}", json={"price_cents": 500})

    # Get order again and verify total didn't change
    order_id = created["id"]
    order = client.get(f"/orders/{order_id}").json()
    assert order["total_cents"] == 200
    assert order["items"][0]["unit_price_cents"] == 100


def test_revenue_by_category_empty(client):
    """Test revenue report with no orders."""
    r = client.get("/reports/revenue-by-category")
    assert r.status_code == 200
    assert r.json() == {}


def test_revenue_by_category_single(client):
    """Test revenue calculation with single order."""
    p = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 10, "category": "tools"}).json()["id"]

    client.post("/orders", json={
        "items": [{"product_id": p, "quantity": 5}]})

    r = client.get("/reports/revenue-by-category")
    assert r.status_code == 200
    revenue = r.json()
    assert revenue["tools"] == 500


def test_revenue_by_category_multiple(client):
    """Test revenue with multiple categories and orders."""
    p1 = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 10, "category": "tools"}).json()["id"]
    p2 = client.post("/products", json={
        "name": "B", "sku": "B1", "price_cents": 200,
        "stock": 10, "category": "gadgets"}).json()["id"]

    # Order 1: 2 units of tools at 100
    client.post("/orders", json={
        "items": [{"product_id": p1, "quantity": 2}]})
    # Order 2: 3 units of gadgets at 200
    client.post("/orders", json={
        "items": [{"product_id": p2, "quantity": 3}]})

    r = client.get("/reports/revenue-by-category")
    revenue = r.json()
    assert revenue["tools"] == 200
    assert revenue["gadgets"] == 600


def test_revenue_excludes_cancelled_orders(client):
    """Test that cancelled orders don't count in revenue."""
    p = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 10, "category": "tools"}).json()["id"]

    # Create two orders
    order1 = client.post("/orders", json={
        "items": [{"product_id": p, "quantity": 2}]}).json()
    order2 = client.post("/orders", json={
        "items": [{"product_id": p, "quantity": 3}]}).json()

    # Cancel first order
    client.post(f"/orders/{order1['id']}/cancel")

    r = client.get("/reports/revenue-by-category")
    revenue = r.json()
    # Only order2 should count: 3 * 100 = 300
    assert revenue["tools"] == 300


def test_revenue_uses_snapshot_prices(client):
    """Test that revenue uses snapshot prices from order time."""
    p = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 10, "category": "tools"}).json()["id"]

    # Create order at price 100
    client.post("/orders", json={
        "items": [{"product_id": p, "quantity": 5}]})

    # Change product price
    client.patch(f"/products/{p}", json={"price_cents": 500})

    # Revenue should use snapshot price (100)
    r = client.get("/reports/revenue-by-category")
    revenue = r.json()
    assert revenue["tools"] == 500  # 5 * 100


def test_delete_product_with_order_409(client):
    """Test referential integrity: cannot delete product with orders."""
    p = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 10, "category": "tools"}).json()["id"]

    # Create order
    client.post("/orders", json={
        "items": [{"product_id": p, "quantity": 2}]})

    # Try to delete product
    r = client.delete(f"/products/{p}")
    assert r.status_code == 409

    # Verify product still exists
    assert client.get(f"/products/{p}").status_code == 200


def test_delete_product_no_order_works(client):
    """Test that deleting product without orders works."""
    p = client.post("/products", json={
        "name": "A", "sku": "A1", "price_cents": 100,
        "stock": 10, "category": "tools"}).json()["id"]

    # Delete product (no orders)
    r = client.delete(f"/products/{p}")
    assert r.status_code == 204

    # Verify product is gone
    assert client.get(f"/products/{p}").status_code == 404


def test_existing_products_tests_still_pass(client):
    """Ensure mevcut product tests still work."""
    r = client.post("/products", json={
        "name": "Widget", "sku": "W1", "price_cents": 500,
        "stock": 10, "category": "tools"})
    assert r.status_code == 201
    pid = r.json()["id"]
    assert client.get(f"/products/{pid}").json()["sku"] == "W1"
