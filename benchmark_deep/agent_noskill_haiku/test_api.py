import os
import sqlite3
import tempfile
import pytest
from fastapi.testclient import TestClient
from main import app, init_db


@pytest.fixture
def client():
    """FastAPI TestClient with isolated in-memory database for each test."""
    # Use a temporary file for each test
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Set environment variable for this test
    os_backup = os.environ.get("DB_PATH")
    os.environ["DB_PATH"] = db_path

    try:
        # Initialize DB
        init_db()
        yield TestClient(app)
    finally:
        # Restore environment and cleanup
        if os_backup is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = os_backup

        # Clean up temp file
        try:
            os.unlink(db_path)
        except:
            pass


# --- Product Tests ---
class TestProducts:
    def test_create_product_success(self, client):
        """Test successful product creation."""
        response = client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 10,
                "category": "Electronics",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Laptop"
        assert data["sku"] == "LAPTOP001"
        assert data["price_cents"] == 100000

    def test_create_product_negative_price(self, client):
        """Test creation with negative price (should fail)."""
        response = client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": -100,
                "stock": 10,
                "category": "Electronics",
            },
        )
        assert response.status_code == 422

    def test_create_product_negative_stock(self, client):
        """Test creation with negative stock (should fail)."""
        response = client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": -5,
                "category": "Electronics",
            },
        )
        assert response.status_code == 422

    def test_create_product_duplicate_sku(self, client):
        """Test creation with duplicate SKU (should fail with 409)."""
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 10,
                "category": "Electronics",
            },
        )
        response = client.post(
            "/products",
            json={
                "name": "Another Laptop",
                "sku": "LAPTOP001",
                "price_cents": 200000,
                "stock": 5,
                "category": "Electronics",
            },
        )
        assert response.status_code == 409

    def test_get_product(self, client):
        """Test fetching a product."""
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 10,
                "category": "Electronics",
            },
        )
        response = client.get("/products/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Laptop"

    def test_get_product_not_found(self, client):
        """Test fetching non-existent product."""
        response = client.get("/products/999")
        assert response.status_code == 404

    def test_list_products(self, client):
        """Test listing products."""
        for i in range(3):
            client.post(
                "/products",
                json={
                    "name": f"Product {i}",
                    "sku": f"SKU{i}",
                    "price_cents": 10000 * (i + 1),
                    "stock": 10,
                    "category": "Electronics" if i < 2 else "Books",
                },
            )

        response = client.get("/products")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_list_products_with_category_filter(self, client):
        """Test listing products with category filter."""
        for i in range(3):
            client.post(
                "/products",
                json={
                    "name": f"Product {i}",
                    "sku": f"SKU{i}",
                    "price_cents": 10000,
                    "stock": 10,
                    "category": "Electronics" if i < 2 else "Books",
                },
            )

        response = client.get("/products?category=Electronics")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(p["category"] == "Electronics" for p in data)

    def test_list_products_pagination(self, client):
        """Test pagination with limit and offset."""
        for i in range(5):
            client.post(
                "/products",
                json={
                    "name": f"Product {i}",
                    "sku": f"SKU{i}",
                    "price_cents": 10000,
                    "stock": 10,
                    "category": "Electronics",
                },
            )

        response = client.get("/products?limit=2&offset=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == 2

    def test_list_products_offset_beyond_range(self, client):
        """Test pagination with offset beyond list size."""
        client.post(
            "/products",
            json={
                "name": "Product 1",
                "sku": "SKU1",
                "price_cents": 10000,
                "stock": 10,
                "category": "Electronics",
            },
        )

        response = client.get("/products?limit=10&offset=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_update_product(self, client):
        """Test updating a product."""
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 10,
                "category": "Electronics",
            },
        )

        response = client.patch("/products/1", json={"price_cents": 150000})
        assert response.status_code == 200
        data = response.json()
        assert data["price_cents"] == 150000
        assert data["name"] == "Laptop"  # Unchanged

    def test_update_product_negative_price(self, client):
        """Test updating product with negative price."""
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 10,
                "category": "Electronics",
            },
        )

        response = client.patch("/products/1", json={"price_cents": -100})
        assert response.status_code == 422

    def test_update_product_not_found(self, client):
        """Test updating non-existent product."""
        response = client.patch("/products/999", json={"price_cents": 150000})
        assert response.status_code == 404

    def test_delete_product(self, client):
        """Test deleting a product."""
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 10,
                "category": "Electronics",
            },
        )

        response = client.delete("/products/1")
        assert response.status_code == 204

        # Verify it's deleted
        response = client.get("/products/1")
        assert response.status_code == 404

    def test_delete_product_not_found(self, client):
        """Test deleting non-existent product."""
        response = client.delete("/products/999")
        assert response.status_code == 404

    def test_delete_product_referenced_in_order(self, client):
        """Test deleting product that's in an order (should fail)."""
        # Create product
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 10,
                "category": "Electronics",
            },
        )

        # Create order with the product
        client.post("/orders", json={"items": [{"product_id": 1, "quantity": 2}]})

        # Try to delete product
        response = client.delete("/products/1")
        assert response.status_code == 409


# --- Order Tests ---
class TestOrders:
    def test_create_order_success(self, client):
        """Test successful order creation."""
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 10,
                "category": "Electronics",
            },
        )

        response = client.post(
            "/orders",
            json={"items": [{"product_id": 1, "quantity": 2}]},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 1
        assert data["status"] == "pending"
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2
        assert data["items"][0]["unit_price_cents"] == 100000
        assert data["total_cents"] == 200000

    def test_create_order_multiple_items(self, client):
        """Test creating order with multiple items."""
        for i in range(2):
            client.post(
                "/products",
                json={
                    "name": f"Product {i}",
                    "sku": f"SKU{i}",
                    "price_cents": 10000 * (i + 1),
                    "stock": 10,
                    "category": "Electronics",
                },
            )

        response = client.post(
            "/orders",
            json={"items": [{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 3}]},
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total_cents"] == (10000 * 2) + (20000 * 3)

    def test_create_order_insufficient_stock(self, client):
        """Test order creation with insufficient stock."""
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 5,
                "category": "Electronics",
            },
        )

        response = client.post(
            "/orders",
            json={"items": [{"product_id": 1, "quantity": 10}]},
        )
        assert response.status_code == 409

    def test_create_order_atomic_stock_reduction(self, client):
        """Test that stock reduction is atomic (partial failure rolls back)."""
        # Create two products
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 10,
                "category": "Electronics",
            },
        )
        client.post(
            "/products",
            json={
                "name": "Mouse",
                "sku": "MOUSE001",
                "price_cents": 5000,
                "stock": 2,
                "category": "Electronics",
            },
        )

        # Try to order more mice than available
        response = client.post(
            "/orders",
            json={"items": [{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 5}]},
        )
        assert response.status_code == 409

        # Verify no stock was reduced
        response = client.get("/products/1")
        assert response.json()["stock"] == 10
        response = client.get("/products/2")
        assert response.json()["stock"] == 2

    def test_create_order_product_not_found(self, client):
        """Test order creation with non-existent product."""
        response = client.post(
            "/orders",
            json={"items": [{"product_id": 999, "quantity": 2}]},
        )
        assert response.status_code == 404

    def test_create_order_negative_quantity(self, client):
        """Test order with negative quantity."""
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 10,
                "category": "Electronics",
            },
        )

        response = client.post(
            "/orders",
            json={"items": [{"product_id": 1, "quantity": -5}]},
        )
        assert response.status_code == 422

    def test_create_order_zero_quantity(self, client):
        """Test order with zero quantity."""
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 10,
                "category": "Electronics",
            },
        )

        response = client.post(
            "/orders",
            json={"items": [{"product_id": 1, "quantity": 0}]},
        )
        assert response.status_code == 422

    def test_create_order_empty_items(self, client):
        """Test order with empty items list."""
        response = client.post("/orders", json={"items": []})
        assert response.status_code == 422

    def test_get_order(self, client):
        """Test fetching an order."""
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 10,
                "category": "Electronics",
            },
        )
        client.post(
            "/orders",
            json={"items": [{"product_id": 1, "quantity": 2}]},
        )

        response = client.get("/orders/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["status"] == "pending"
        assert data["total_cents"] == 200000

    def test_get_order_not_found(self, client):
        """Test fetching non-existent order."""
        response = client.get("/orders/999")
        assert response.status_code == 404

    def test_price_snapshot_isolation(self, client):
        """Test that price snapshot is isolated from later price changes."""
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 10,
                "category": "Electronics",
            },
        )

        # Create order
        response = client.post(
            "/orders",
            json={"items": [{"product_id": 1, "quantity": 2}]},
        )
        order_total = response.json()["total_cents"]

        # Update product price
        client.patch("/products/1", json={"price_cents": 150000})

        # Verify order total didn't change
        response = client.get("/orders/1")
        assert response.json()["total_cents"] == order_total

    def test_cancel_order_success(self, client):
        """Test cancelling an order."""
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 10,
                "category": "Electronics",
            },
        )

        # Create and cancel order
        client.post(
            "/orders",
            json={"items": [{"product_id": 1, "quantity": 2}]},
        )
        response = client.post("/orders/1/cancel")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

        # Verify stock was restored
        response = client.get("/products/1")
        assert response.json()["stock"] == 10

    def test_cancel_order_not_found(self, client):
        """Test cancelling non-existent order."""
        response = client.post("/orders/999/cancel")
        assert response.status_code == 404

    def test_cancel_order_already_cancelled_idempotency(self, client):
        """Test cancelling an already cancelled order (idempotency)."""
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 10,
                "category": "Electronics",
            },
        )

        # Create and cancel order once
        client.post(
            "/orders",
            json={"items": [{"product_id": 1, "quantity": 2}]},
        )
        client.post("/orders/1/cancel")

        # Verify stock after first cancel
        response = client.get("/products/1")
        stock_after_first_cancel = response.json()["stock"]

        # Try to cancel again
        response = client.post("/orders/1/cancel")
        assert response.status_code == 409

        # Verify stock didn't change (not re-added)
        response = client.get("/products/1")
        assert response.json()["stock"] == stock_after_first_cancel

    def test_cancel_order_multiple_items(self, client):
        """Test cancelling order with multiple items restores all stock."""
        for i in range(2):
            client.post(
                "/products",
                json={
                    "name": f"Product {i}",
                    "sku": f"SKU{i}",
                    "price_cents": 10000,
                    "stock": 10,
                    "category": "Electronics",
                },
            )

        # Create order
        client.post(
            "/orders",
            json={"items": [{"product_id": 1, "quantity": 3}, {"product_id": 2, "quantity": 5}]},
        )

        # Cancel order
        client.post("/orders/1/cancel")

        # Verify both stocks were restored
        response = client.get("/products/1")
        assert response.json()["stock"] == 10
        response = client.get("/products/2")
        assert response.json()["stock"] == 10


# --- Report Tests ---
class TestReports:
    def test_low_stock_report_default_threshold(self, client):
        """Test low stock report with default threshold."""
        for i in range(3):
            client.post(
                "/products",
                json={
                    "name": f"Product {i}",
                    "sku": f"SKU{i}",
                    "price_cents": 10000,
                    "stock": i * 5,  # 0, 5, 10
                    "category": "Electronics",
                },
            )

        response = client.get("/reports/low-stock")
        assert response.status_code == 200
        data = response.json()
        # Default threshold is 10, so should get products with stock 0, 5, 10
        assert len(data) == 3

    def test_low_stock_report_custom_threshold(self, client):
        """Test low stock report with custom threshold."""
        for i in range(3):
            client.post(
                "/products",
                json={
                    "name": f"Product {i}",
                    "sku": f"SKU{i}",
                    "price_cents": 10000,
                    "stock": i * 10,  # 0, 10, 20
                    "category": "Electronics",
                },
            )

        response = client.get("/reports/low-stock?threshold=5")
        assert response.status_code == 200
        data = response.json()
        # Threshold 5, so should get product with stock 0
        assert len(data) == 1
        assert data[0]["stock"] == 0

    def test_low_stock_report_empty(self, client):
        """Test low stock report when no products are low stock."""
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 100,
                "category": "Electronics",
            },
        )

        response = client.get("/reports/low-stock?threshold=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_revenue_by_category(self, client):
        """Test revenue by category report."""
        # Create products
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 10,
                "category": "Electronics",
            },
        )
        client.post(
            "/products",
            json={
                "name": "Book",
                "sku": "BOOK001",
                "price_cents": 1000,
                "stock": 100,
                "category": "Books",
            },
        )

        # Create orders
        client.post(
            "/orders",
            json={"items": [{"product_id": 1, "quantity": 2}]},
        )
        client.post(
            "/orders",
            json={"items": [{"product_id": 2, "quantity": 5}]},
        )

        response = client.get("/reports/revenue-by-category")
        assert response.status_code == 200
        data = response.json()
        assert data["Electronics"] == 200000
        assert data["Books"] == 5000

    def test_revenue_by_category_excludes_cancelled(self, client):
        """Test that cancelled orders are excluded from revenue."""
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 10,
                "category": "Electronics",
            },
        )

        # Create order
        client.post(
            "/orders",
            json={"items": [{"product_id": 1, "quantity": 2}]},
        )

        # Cancel the order
        client.post("/orders/1/cancel")

        response = client.get("/reports/revenue-by-category")
        assert response.status_code == 200
        data = response.json()
        # No non-cancelled orders, so no revenue
        assert "Electronics" not in data or data.get("Electronics", 0) == 0

    def test_revenue_by_category_mixed_statuses(self, client):
        """Test revenue calculation with mixed order statuses."""
        client.post(
            "/products",
            json={
                "name": "Laptop",
                "sku": "LAPTOP001",
                "price_cents": 100000,
                "stock": 20,
                "category": "Electronics",
            },
        )

        # Create two orders
        client.post(
            "/orders",
            json={"items": [{"product_id": 1, "quantity": 2}]},
        )
        client.post(
            "/orders",
            json={"items": [{"product_id": 1, "quantity": 3}]},
        )

        # Cancel first order
        client.post("/orders/1/cancel")

        # Only second order should count
        response = client.get("/reports/revenue-by-category")
        assert response.status_code == 200
        data = response.json()
        assert data["Electronics"] == 300000
