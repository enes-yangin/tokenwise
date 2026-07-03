import os
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Fixture: set test database and create fresh schema for each test."""
    os.environ["DATABASE_URL"] = ":memory:"
    # Import here to reload the module with test env var
    import importlib
    import main
    importlib.reload(main)
    yield TestClient(main.app)


# ===== PRODUCTS TESTS =====

def test_create_product(client):
    """POST /products: create a new product."""
    resp = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Laptop"
    assert data["sku"] == "LAPTOP001"
    assert data["price_cents"] == 100000
    assert data["stock"] == 10
    assert data["category"] == "Electronics"
    assert "id" in data


def test_create_product_duplicate_sku(client):
    """POST /products: 409 if SKU already exists."""
    client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    })
    resp = client.post("/products", json={
        "name": "Laptop 2",
        "sku": "LAPTOP001",
        "price_cents": 200000,
        "stock": 5,
        "category": "Electronics"
    })
    assert resp.status_code == 409


def test_create_product_negative_price(client):
    """POST /products: 422 if price_cents < 0."""
    resp = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": -100,
        "stock": 10,
        "category": "Electronics"
    })
    assert resp.status_code == 422


def test_create_product_negative_stock(client):
    """POST /products: 422 if stock < 0."""
    resp = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": -5,
        "category": "Electronics"
    })
    assert resp.status_code == 422


def test_create_product_missing_field(client):
    """POST /products: 422 if required field missing."""
    resp = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        # missing price_cents
        "stock": 10,
        "category": "Electronics"
    })
    assert resp.status_code == 422


def test_get_product(client):
    """GET /products/{id}: retrieve product by ID."""
    created = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    }).json()

    resp = client.get(f"/products/{created['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == created["id"]
    assert data["name"] == "Laptop"


def test_get_product_not_found(client):
    """GET /products/{id}: 404 if product doesn't exist."""
    resp = client.get("/products/999")
    assert resp.status_code == 404


def test_list_products(client):
    """GET /products: list all products with pagination."""
    # Create 5 products
    for i in range(5):
        client.post("/products", json={
            "name": f"Product {i}",
            "sku": f"SKU{i}",
            "price_cents": 1000 + i * 100,
            "stock": 10,
            "category": "Electronics" if i % 2 == 0 else "Books"
        })

    # Default: limit=50, offset=0
    resp = client.get("/products")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5

    # With limit and offset
    resp = client.get("/products?limit=2&offset=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    # Offset beyond list
    resp = client.get("/products?offset=100")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 0


def test_list_products_filter_by_category(client):
    """GET /products?category=<str>: filter by category."""
    client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    })
    client.post("/products", json={
        "name": "Book",
        "sku": "BOOK001",
        "price_cents": 5000,
        "stock": 50,
        "category": "Books"
    })

    resp = client.get("/products?category=Electronics")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["category"] == "Electronics"


def test_patch_product(client):
    """PATCH /products/{id}: update product fields."""
    created = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    }).json()

    # Update price
    resp = client.patch(f"/products/{created['id']}", json={"price_cents": 120000})
    assert resp.status_code == 200
    data = resp.json()
    assert data["price_cents"] == 120000
    assert data["name"] == "Laptop"  # unchanged

    # Update stock
    resp = client.patch(f"/products/{created['id']}", json={"stock": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["stock"] == 5
    assert data["price_cents"] == 120000  # unchanged


def test_patch_product_not_found(client):
    """PATCH /products/{id}: 404 if product doesn't exist."""
    resp = client.patch("/products/999", json={"price_cents": 200000})
    assert resp.status_code == 404


def test_delete_product(client):
    """DELETE /products/{id}: delete product."""
    created = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    }).json()

    resp = client.delete(f"/products/{created['id']}")
    assert resp.status_code == 204

    # Verify deletion
    resp = client.get(f"/products/{created['id']}")
    assert resp.status_code == 404


def test_delete_product_not_found(client):
    """DELETE /products/{id}: 404 if product doesn't exist."""
    resp = client.delete("/products/999")
    assert resp.status_code == 404


def test_delete_product_referenced_in_order(client):
    """DELETE /products/{id}: 409 if product is in an OrderItem."""
    # Create product and order
    product = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    }).json()

    order = client.post("/orders", json={
        "items": [{"product_id": product["id"], "quantity": 1}]
    }).json()

    # Try to delete product that's in order
    resp = client.delete(f"/products/{product['id']}")
    assert resp.status_code == 409


# ===== ORDERS TESTS =====

def test_create_order(client):
    """POST /orders: create order with items."""
    product = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    }).json()

    resp = client.post("/orders", json={
        "items": [{"product_id": product["id"], "quantity": 2}]
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert "created_at" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == product["id"]
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["unit_price_cents"] == 100000  # snapshot
    assert data["total_cents"] == 200000


def test_create_order_multiple_items(client):
    """POST /orders: create order with multiple items."""
    p1 = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    }).json()

    p2 = client.post("/products", json={
        "name": "Mouse",
        "sku": "MOUSE001",
        "price_cents": 5000,
        "stock": 20,
        "category": "Electronics"
    }).json()

    resp = client.post("/orders", json={
        "items": [
            {"product_id": p1["id"], "quantity": 1},
            {"product_id": p2["id"], "quantity": 3}
        ]
    })
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total_cents"] == 100000 + 15000  # 1*100000 + 3*5000


def test_create_order_reduces_stock(client):
    """POST /orders: stock is reduced for ordered products."""
    product = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    }).json()

    client.post("/orders", json={
        "items": [{"product_id": product["id"], "quantity": 3}]
    })

    # Verify stock reduced
    updated = client.get(f"/products/{product['id']}").json()
    assert updated["stock"] == 7


def test_create_order_insufficient_stock(client):
    """POST /orders: 409 if insufficient stock."""
    product = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 5,
        "category": "Electronics"
    }).json()

    resp = client.post("/orders", json={
        "items": [{"product_id": product["id"], "quantity": 10}]
    })
    assert resp.status_code == 409


def test_create_order_insufficient_stock_atomic(client):
    """POST /orders: 409 with multiple items → NO partial stock reduction."""
    p1 = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    }).json()

    p2 = client.post("/products", json={
        "name": "Mouse",
        "sku": "MOUSE001",
        "price_cents": 5000,
        "stock": 2,
        "category": "Electronics"
    }).json()

    # Try order: p1 ok (qty 2), p2 fails (qty 5, only 2 available)
    resp = client.post("/orders", json={
        "items": [
            {"product_id": p1["id"], "quantity": 2},
            {"product_id": p2["id"], "quantity": 5}
        ]
    })
    assert resp.status_code == 409

    # Verify NO stock was reduced (atomicity)
    assert client.get(f"/products/{p1['id']}").json()["stock"] == 10
    assert client.get(f"/products/{p2['id']}").json()["stock"] == 2


def test_create_order_product_not_found(client):
    """POST /orders: 404 if product doesn't exist."""
    resp = client.post("/orders", json={
        "items": [{"product_id": 999, "quantity": 1}]
    })
    assert resp.status_code == 404


def test_create_order_zero_quantity(client):
    """POST /orders: 422 if quantity <= 0."""
    product = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    }).json()

    resp = client.post("/orders", json={
        "items": [{"product_id": product["id"], "quantity": 0}]
    })
    assert resp.status_code == 422


def test_create_order_empty_items(client):
    """POST /orders: 422 if items list is empty."""
    resp = client.post("/orders", json={"items": []})
    assert resp.status_code == 422


def test_get_order(client):
    """GET /orders/{id}: retrieve order with items and total."""
    product = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    }).json()

    created = client.post("/orders", json={
        "items": [{"product_id": product["id"], "quantity": 2}]
    }).json()

    resp = client.get(f"/orders/{created['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == created["id"]
    assert data["status"] == "pending"
    assert len(data["items"]) == 1
    assert data["total_cents"] == 200000


def test_get_order_not_found(client):
    """GET /orders/{id}: 404 if order doesn't exist."""
    resp = client.get("/orders/999")
    assert resp.status_code == 404


def test_cancel_order(client):
    """POST /orders/{id}/cancel: mark order as cancelled."""
    product = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    }).json()

    order = client.post("/orders", json={
        "items": [{"product_id": product["id"], "quantity": 2}]
    }).json()

    # Stock reduced
    assert client.get(f"/products/{product['id']}").json()["stock"] == 8

    # Cancel order
    resp = client.post(f"/orders/{order['id']}/cancel")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "cancelled"

    # Stock restored
    assert client.get(f"/products/{product['id']}").json()["stock"] == 10


def test_cancel_order_not_found(client):
    """POST /orders/{id}/cancel: 404 if order doesn't exist."""
    resp = client.post("/orders/999/cancel")
    assert resp.status_code == 404


def test_cancel_order_already_cancelled(client):
    """POST /orders/{id}/cancel: 409 if already cancelled (idempotency)."""
    product = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    }).json()

    order = client.post("/orders", json={
        "items": [{"product_id": product["id"], "quantity": 2}]
    }).json()

    # First cancel
    resp1 = client.post(f"/orders/{order['id']}/cancel")
    assert resp1.status_code == 200

    # Second cancel
    resp2 = client.post(f"/orders/{order['id']}/cancel")
    assert resp2.status_code == 409

    # Verify stock only restored once
    assert client.get(f"/products/{product['id']}").json()["stock"] == 10


def test_cancel_order_restores_all_items(client):
    """POST /orders/{id}/cancel: restore stock for all items."""
    p1 = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    }).json()

    p2 = client.post("/products", json={
        "name": "Mouse",
        "sku": "MOUSE001",
        "price_cents": 5000,
        "stock": 20,
        "category": "Electronics"
    }).json()

    order = client.post("/orders", json={
        "items": [
            {"product_id": p1["id"], "quantity": 2},
            {"product_id": p2["id"], "quantity": 3}
        ]
    }).json()

    # Cancel
    client.post(f"/orders/{order['id']}/cancel")

    # Verify both stocks restored
    assert client.get(f"/products/{p1['id']}").json()["stock"] == 10
    assert client.get(f"/products/{p2['id']}").json()["stock"] == 20


# ===== REPORTS TESTS =====

def test_report_low_stock(client):
    """GET /reports/low-stock: list products with stock <= threshold."""
    client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 5,
        "category": "Electronics"
    })
    client.post("/products", json={
        "name": "Mouse",
        "sku": "MOUSE001",
        "price_cents": 5000,
        "stock": 15,
        "category": "Electronics"
    })

    resp = client.get("/reports/low-stock?threshold=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Laptop"


def test_report_low_stock_default_threshold(client):
    """GET /reports/low-stock: default threshold=10."""
    client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 5,
        "category": "Electronics"
    })

    resp = client.get("/reports/low-stock")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1


def test_report_revenue_by_category(client):
    """GET /reports/revenue-by-category: revenue from non-cancelled orders."""
    p1 = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    }).json()

    p2 = client.post("/products", json={
        "name": "Book",
        "sku": "BOOK001",
        "price_cents": 5000,
        "stock": 50,
        "category": "Books"
    }).json()

    # Order 1: Electronics
    o1 = client.post("/orders", json={
        "items": [{"product_id": p1["id"], "quantity": 1}]
    }).json()

    # Order 2: Books + Electronics
    o2 = client.post("/orders", json={
        "items": [
            {"product_id": p1["id"], "quantity": 1},
            {"product_id": p2["id"], "quantity": 2}
        ]
    }).json()

    # Cancel order 2
    client.post(f"/orders/{o2['id']}/cancel")

    # Only o1 (Electronics 100000) counts
    resp = client.get("/reports/revenue-by-category")
    assert resp.status_code == 200
    data = resp.json()
    assert data["Electronics"] == 100000
    assert data.get("Books", 0) == 0


def test_report_revenue_by_category_uses_snapshots(client):
    """GET /reports/revenue-by-category: uses snapshot prices, not current."""
    product = client.post("/products", json={
        "name": "Laptop",
        "sku": "LAPTOP001",
        "price_cents": 100000,
        "stock": 10,
        "category": "Electronics"
    }).json()

    # Order at price 100000
    order = client.post("/orders", json={
        "items": [{"product_id": product["id"], "quantity": 1}]
    }).json()

    # Change price to 150000
    client.patch(f"/products/{product['id']}", json={"price_cents": 150000})

    # Revenue report should use snapshot 100000, not current 150000
    resp = client.get("/reports/revenue-by-category")
    data = resp.json()
    assert data["Electronics"] == 100000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
