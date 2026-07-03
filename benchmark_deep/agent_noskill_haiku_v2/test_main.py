import os
import sqlite3
import tempfile
from fastapi.testclient import TestClient
import pytest

@pytest.fixture
def client():
    """Create a test client with a fresh temporary database."""
    # Create a temporary database file for this test
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Set the database path before importing main
    os.environ["DB_PATH"] = db_path

    # Import/reimport main to use the new DB_PATH
    import importlib
    import main
    importlib.reload(main)

    test_client = TestClient(main.app)

    yield test_client

    # Clean up the temporary database file
    try:
        os.remove(db_path)
    except:
        pass

class TestProducts:
    """Test product endpoints."""

    def test_create_product_success(self, client):
        """Test creating a product."""
        response = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 50,
            "category": "tools"
        })
        assert response.status_code == 201
        data = response.json()
        assert data['id'] == 1
        assert data['name'] == "Widget"
        assert data['sku'] == "WID-001"
        assert data['price_cents'] == 1000
        assert data['stock'] == 50
        assert data['category'] == "tools"

    def test_create_product_duplicate_sku(self, client):
        """Test that duplicate SKUs return 409."""
        client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 50,
            "category": "tools"
        })
        response = client.post("/products", json={
            "name": "Widget2",
            "sku": "WID-001",
            "price_cents": 2000,
            "stock": 100,
            "category": "tools"
        })
        assert response.status_code == 409
        assert "SKU already exists" in response.json()['detail']

    def test_create_product_negative_price(self, client):
        """Test that negative price returns 422."""
        response = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": -100,
            "stock": 50,
            "category": "tools"
        })
        assert response.status_code == 422

    def test_create_product_negative_stock(self, client):
        """Test that negative stock returns 422."""
        response = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": -50,
            "category": "tools"
        })
        assert response.status_code == 422

    def test_create_product_missing_field(self, client):
        """Test that missing fields return 422."""
        response = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000
            # missing stock and category
        })
        assert response.status_code == 422

    def test_list_products(self, client):
        """Test listing products."""
        # Create some products
        for i in range(5):
            client.post("/products", json={
                "name": f"Widget{i}",
                "sku": f"WID-{i:03d}",
                "price_cents": 1000 + i * 100,
                "stock": 50 + i * 10,
                "category": "tools" if i % 2 == 0 else "gadgets"
            })

        response = client.get("/products")
        assert response.status_code == 200
        assert len(response.json()) == 5

    def test_list_products_with_category_filter(self, client):
        """Test listing products filtered by category."""
        # Create products
        for i in range(5):
            client.post("/products", json={
                "name": f"Widget{i}",
                "sku": f"WID-{i:03d}",
                "price_cents": 1000,
                "stock": 50,
                "category": "tools" if i % 2 == 0 else "gadgets"
            })

        response = client.get("/products?category=tools")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3  # 0, 2, 4
        assert all(p['category'] == 'tools' for p in data)

    def test_list_products_pagination(self, client):
        """Test pagination with limit and offset."""
        # Create 10 products
        for i in range(10):
            client.post("/products", json={
                "name": f"Widget{i}",
                "sku": f"WID-{i:03d}",
                "price_cents": 1000,
                "stock": 50,
                "category": "tools"
            })

        # Test limit
        response = client.get("/products?limit=3")
        assert len(response.json()) == 3

        # Test offset
        response = client.get("/products?limit=3&offset=3")
        data = response.json()
        assert len(data) == 3
        assert data[0]['id'] == 4

    def test_list_products_empty_offset(self, client):
        """Test that offset beyond list size returns empty."""
        client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 50,
            "category": "tools"
        })

        response = client.get("/products?offset=100")
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_get_product(self, client):
        """Test getting a specific product."""
        create_resp = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 50,
            "category": "tools"
        })
        product_id = create_resp.json()['id']

        response = client.get(f"/products/{product_id}")
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == product_id
        assert data['name'] == "Widget"

    def test_get_product_not_found(self, client):
        """Test getting a non-existent product."""
        response = client.get("/products/999")
        assert response.status_code == 404

    def test_patch_product(self, client):
        """Test patching a product."""
        create_resp = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 50,
            "category": "tools"
        })
        product_id = create_resp.json()['id']

        response = client.patch(f"/products/{product_id}", json={
            "price_cents": 2000,
            "stock": 100
        })
        assert response.status_code == 200
        data = response.json()
        assert data['price_cents'] == 2000
        assert data['stock'] == 100
        assert data['name'] == "Widget"  # unchanged

    def test_patch_product_not_found(self, client):
        """Test patching a non-existent product."""
        response = client.patch("/products/999", json={"price_cents": 2000})
        assert response.status_code == 404

    def test_delete_product(self, client):
        """Test deleting a product."""
        create_resp = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 50,
            "category": "tools"
        })
        product_id = create_resp.json()['id']

        response = client.delete(f"/products/{product_id}")
        assert response.status_code == 204

        # Verify it's deleted
        response = client.get(f"/products/{product_id}")
        assert response.status_code == 404

    def test_delete_product_not_found(self, client):
        """Test deleting a non-existent product."""
        response = client.delete("/products/999")
        assert response.status_code == 404

    def test_delete_product_referenced_in_order(self, client):
        """Test that deleting a product with orders fails."""
        # Create product
        prod_resp = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 50,
            "category": "tools"
        })
        product_id = prod_resp.json()['id']

        # Create order with that product
        order_resp = client.post("/orders", json={
            "items": [{"product_id": product_id, "quantity": 5}]
        })
        assert order_resp.status_code == 201

        # Try to delete
        response = client.delete(f"/products/{product_id}")
        assert response.status_code == 409
        assert "referenced" in response.json()['detail'].lower()

        # Verify product still exists
        response = client.get(f"/products/{product_id}")
        assert response.status_code == 200

class TestOrders:
    """Test order endpoints."""

    def test_create_order_success(self, client):
        """Test creating an order."""
        # Create products
        prod1 = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 50,
            "category": "tools"
        }).json()

        prod2 = client.post("/products", json={
            "name": "Gadget",
            "sku": "GAD-001",
            "price_cents": 2000,
            "stock": 30,
            "category": "gadgets"
        }).json()

        # Create order
        response = client.post("/orders", json={
            "items": [
                {"product_id": prod1['id'], "quantity": 5},
                {"product_id": prod2['id'], "quantity": 3}
            ]
        })
        assert response.status_code == 201
        data = response.json()
        assert data['id'] == 1
        assert data['status'] == 'pending'
        assert len(data['items']) == 2
        assert data['total_cents'] == 5 * 1000 + 3 * 2000

    def test_create_order_stock_decremented(self, client):
        """Test that stock is decremented when order is created."""
        prod = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 50,
            "category": "tools"
        }).json()

        client.post("/orders", json={
            "items": [{"product_id": prod['id'], "quantity": 10}]
        })

        # Check stock
        response = client.get(f"/products/{prod['id']}")
        assert response.json()['stock'] == 40

    def test_create_order_insufficient_stock(self, client):
        """Test that insufficient stock returns 409."""
        prod = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 10,
            "category": "tools"
        }).json()

        response = client.post("/orders", json={
            "items": [{"product_id": prod['id'], "quantity": 50}]
        })
        assert response.status_code == 409

    def test_create_order_insufficient_stock_no_partial_update(self, client):
        """Test atomic stock update (no partial update on failure)."""
        prod1 = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 50,
            "category": "tools"
        }).json()

        prod2 = client.post("/products", json={
            "name": "Gadget",
            "sku": "GAD-001",
            "price_cents": 2000,
            "stock": 5,  # Not enough
            "category": "gadgets"
        }).json()

        # Try to create order that fails
        response = client.post("/orders", json={
            "items": [
                {"product_id": prod1['id'], "quantity": 10},
                {"product_id": prod2['id'], "quantity": 10}
            ]
        })
        assert response.status_code == 409

        # Verify no stock was changed
        assert client.get(f"/products/{prod1['id']}").json()['stock'] == 50
        assert client.get(f"/products/{prod2['id']}").json()['stock'] == 5

    def test_create_order_product_not_found(self, client):
        """Test that non-existent product returns 404."""
        response = client.post("/orders", json={
            "items": [{"product_id": 999, "quantity": 5}]
        })
        assert response.status_code == 404

    def test_create_order_invalid_quantity(self, client):
        """Test that quantity <= 0 returns 422."""
        prod = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 50,
            "category": "tools"
        }).json()

        response = client.post("/orders", json={
            "items": [{"product_id": prod['id'], "quantity": 0}]
        })
        assert response.status_code == 422

        response = client.post("/orders", json={
            "items": [{"product_id": prod['id'], "quantity": -5}]
        })
        assert response.status_code == 422

    def test_create_order_empty_items(self, client):
        """Test that empty items list returns 422."""
        response = client.post("/orders", json={"items": []})
        assert response.status_code == 422

    def test_get_order(self, client):
        """Test getting an order."""
        prod = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 50,
            "category": "tools"
        }).json()

        order_resp = client.post("/orders", json={
            "items": [{"product_id": prod['id'], "quantity": 5}]
        })
        order_id = order_resp.json()['id']

        response = client.get(f"/orders/{order_id}")
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == order_id
        assert data['status'] == 'pending'
        assert len(data['items']) == 1
        assert data['items'][0]['quantity'] == 5
        assert data['items'][0]['unit_price_cents'] == 1000
        assert data['total_cents'] == 5000

    def test_get_order_not_found(self, client):
        """Test getting a non-existent order."""
        response = client.get("/orders/999")
        assert response.status_code == 404

    def test_cancel_order_success(self, client):
        """Test cancelling an order."""
        prod = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 50,
            "category": "tools"
        }).json()

        order_resp = client.post("/orders", json={
            "items": [{"product_id": prod['id'], "quantity": 10}]
        })
        order_id = order_resp.json()['id']

        # Cancel order
        response = client.post(f"/orders/{order_id}/cancel")
        assert response.status_code == 200
        assert response.json()['status'] == 'cancelled'

        # Check stock restored
        assert client.get(f"/products/{prod['id']}").json()['stock'] == 50

    def test_cancel_order_already_cancelled(self, client):
        """Test that cancelling already cancelled order returns 409."""
        prod = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 50,
            "category": "tools"
        }).json()

        order_resp = client.post("/orders", json={
            "items": [{"product_id": prod['id'], "quantity": 10}]
        })
        order_id = order_resp.json()['id']

        # Cancel once
        client.post(f"/orders/{order_id}/cancel")

        # Try to cancel again
        response = client.post(f"/orders/{order_id}/cancel")
        assert response.status_code == 409

        # Verify stock not double-restored
        assert client.get(f"/products/{prod['id']}").json()['stock'] == 50

    def test_cancel_order_not_found(self, client):
        """Test cancelling non-existent order."""
        response = client.post("/orders/999/cancel")
        assert response.status_code == 404

    def test_price_snapshot(self, client):
        """Test that order captures price snapshot."""
        prod = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 50,
            "category": "tools"
        }).json()

        order_resp = client.post("/orders", json={
            "items": [{"product_id": prod['id'], "quantity": 5}]
        })
        order_id = order_resp.json()['id']
        assert order_resp.json()['total_cents'] == 5000

        # Update product price
        client.patch(f"/products/{prod['id']}", json={"price_cents": 2000})

        # Check order still has old price
        order_data = client.get(f"/orders/{order_id}").json()
        assert order_data['total_cents'] == 5000
        assert order_data['items'][0]['unit_price_cents'] == 1000

class TestReports:
    """Test report endpoints."""

    def test_low_stock_report(self, client):
        """Test low stock report."""
        client.post("/products", json={
            "name": "Widget1",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 5,
            "category": "tools"
        })
        client.post("/products", json={
            "name": "Widget2",
            "sku": "WID-002",
            "price_cents": 1000,
            "stock": 15,
            "category": "tools"
        })
        client.post("/products", json={
            "name": "Widget3",
            "sku": "WID-003",
            "price_cents": 1000,
            "stock": 50,
            "category": "tools"
        })

        response = client.get("/reports/low-stock?threshold=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]['name'] == "Widget1"

    def test_low_stock_report_default_threshold(self, client):
        """Test low stock report with default threshold."""
        for i in range(15):
            client.post("/products", json={
                "name": f"Widget{i}",
                "sku": f"WID-{i:03d}",
                "price_cents": 1000,
                "stock": i,  # 0 to 14
                "category": "tools"
            })

        response = client.get("/reports/low-stock")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 11  # 0-10 inclusive

    def test_revenue_by_category(self, client):
        """Test revenue by category report."""
        prod1 = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 100,
            "category": "tools"
        }).json()

        prod2 = client.post("/products", json={
            "name": "Gadget",
            "sku": "GAD-001",
            "price_cents": 2000,
            "stock": 100,
            "category": "gadgets"
        }).json()

        # Create orders
        client.post("/orders", json={
            "items": [
                {"product_id": prod1['id'], "quantity": 5},
                {"product_id": prod2['id'], "quantity": 3}
            ]
        })

        response = client.get("/reports/revenue-by-category")
        assert response.status_code == 200
        data = response.json()
        assert data['tools'] == 5000
        assert data['gadgets'] == 6000

    def test_revenue_by_category_excludes_cancelled(self, client):
        """Test that revenue excludes cancelled orders."""
        prod = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 100,
            "category": "tools"
        }).json()

        # Create and cancel order
        order_resp = client.post("/orders", json={
            "items": [{"product_id": prod['id'], "quantity": 10}]
        })
        order_id = order_resp.json()['id']
        client.post(f"/orders/{order_id}/cancel")

        # Create another order
        client.post("/orders", json={
            "items": [{"product_id": prod['id'], "quantity": 5}]
        })

        response = client.get("/reports/revenue-by-category")
        assert response.status_code == 200
        data = response.json()
        assert data['tools'] == 5000  # Only the non-cancelled order

    def test_revenue_by_category_price_snapshot(self, client):
        """Test that revenue uses snapshot prices."""
        prod = client.post("/products", json={
            "name": "Widget",
            "sku": "WID-001",
            "price_cents": 1000,
            "stock": 100,
            "category": "tools"
        }).json()

        # Create order
        client.post("/orders", json={
            "items": [{"product_id": prod['id'], "quantity": 10}]
        })

        # Update price
        client.patch(f"/products/{prod['id']}", json={"price_cents": 2000})

        # Create another order at new price
        client.post("/orders", json={
            "items": [{"product_id": prod['id'], "quantity": 5}]
        })

        response = client.get("/reports/revenue-by-category")
        assert response.status_code == 200
        data = response.json()
        assert data['tools'] == 10000 + 10000  # 10*1000 + 5*2000
