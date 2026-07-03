"""Order iş mantığı — domain kuralları, HTTPException fırlatır."""
import sqlite3

from fastapi import HTTPException

from app.repositories import order_repo, product_repo


def create_order(conn: sqlite3.Connection, items_in: list) -> dict:
    # Aggregate quantities per product in case of duplicate product_id entries.
    quantities: dict[int, int] = {}
    for item in items_in:
        quantities[item["product_id"]] = quantities.get(item["product_id"], 0) + item["quantity"]

    resolved = []
    for product_id, quantity in quantities.items():
        product = product_repo.get(conn, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail=f"product {product_id} not found")
        if product["stock"] < quantity:
            raise HTTPException(
                status_code=409, detail=f"insufficient stock for product {product_id}"
            )
        resolved.append(
            {
                "product_id": product_id,
                "quantity": quantity,
                "unit_price_cents": product["price_cents"],
            }
        )

    for item in resolved:
        product_repo.adjust_stock(conn, item["product_id"], -item["quantity"])

    return order_repo.create(conn, resolved)


def get_order(conn: sqlite3.Connection, order_id: int) -> dict:
    order = order_repo.get(conn, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order


def cancel_order(conn: sqlite3.Connection, order_id: int) -> dict:
    order = get_order(conn, order_id)
    if order["status"] == "cancelled":
        raise HTTPException(status_code=409, detail="order already cancelled")
    for item in order["items"]:
        product_repo.adjust_stock(conn, item["product_id"], item["quantity"])
    order_repo.set_status(conn, order_id, "cancelled")
    return order_repo.get(conn, order_id)


def revenue_by_category(conn: sqlite3.Connection) -> dict:
    return order_repo.revenue_by_category(conn)
