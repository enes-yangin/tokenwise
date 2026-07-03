"""Order iş mantığı — domain kuralları, HTTPException fırlatır."""
import sqlite3
from collections import defaultdict

from fastapi import HTTPException

from app.repositories import order_repo, product_repo


def create_order(conn: sqlite3.Connection, items_data: list) -> dict:
    """Create order with atomicity: check all items, reserve stock, then commit."""
    # Validate items exist and aggregate quantities by product
    product_totals = defaultdict(int)
    items_with_prices = []

    for item in items_data:
        # Handle both dict and Pydantic model
        product_id = item.product_id if hasattr(item, 'product_id') else item["product_id"]
        quantity = item.quantity if hasattr(item, 'quantity') else item["quantity"]

        # Fetch product
        product = product_repo.get(conn, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="product not found")

        # Check stock
        product_totals[product_id] += quantity
        if product_totals[product_id] > product["stock"]:
            raise HTTPException(
                status_code=409,
                detail="insufficient stock"
            )

        items_with_prices.append({
            "product_id": product_id,
            "quantity": quantity,
            "unit_price_cents": product["price_cents"],
        })

    # Calculate total
    total_cents = sum(
        item["quantity"] * item["unit_price_cents"]
        for item in items_with_prices
    )

    # Atomically adjust stock for all products
    for product_id, total_qty in product_totals.items():
        product_repo.adjust_stock(conn, product_id, -total_qty)

    # Create order
    return order_repo.create(conn, total_cents, items_with_prices)


def get_order(conn: sqlite3.Connection, order_id: int) -> dict:
    order = order_repo.get(conn, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order


def cancel_order(conn: sqlite3.Connection, order_id: int) -> dict:
    order = order_repo.get(conn, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")

    if order["status"] == "cancelled":
        raise HTTPException(status_code=409, detail="order already cancelled")

    # Restore stock for all items
    for item in order["items"]:
        product_repo.adjust_stock(conn, item["product_id"], item["quantity"])

    return order_repo.update_status(conn, order_id, "cancelled")


def get_revenue_by_category(conn: sqlite3.Connection) -> dict:
    """Calculate revenue by category from non-cancelled orders using snapshot prices."""
    items = order_repo.get_all_active_items(conn)
    revenue_by_category = {}

    for item in items:
        category = item["category"]
        revenue = item["quantity"] * item["unit_price_cents"]
        revenue_by_category[category] = revenue_by_category.get(category, 0) + revenue

    return revenue_by_category
