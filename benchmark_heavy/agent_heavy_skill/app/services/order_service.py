"""Order iş mantığı — domain kuralları, HTTPException fırlatır."""
import sqlite3
from collections import defaultdict

from fastapi import HTTPException

from app.repositories import order_repo, product_repo


def _serialize(conn: sqlite3.Connection, order: dict) -> dict:
    items = order_repo.get_items(conn, order["id"])
    total = sum(it["quantity"] * it["unit_price_cents"] for it in items)
    return {
        "id": order["id"],
        "status": order["status"],
        "created_at": order["created_at"],
        "items": items,
        "total_cents": total,
    }


def create_order(conn: sqlite3.Connection, data: dict) -> dict:
    raw_items = data["items"]

    # Aynı ürünün çoklu satırları için toplam miktarı stok kontrolünde topla.
    totals = defaultdict(int)
    for it in raw_items:
        totals[it["product_id"]] += it["quantity"]

    products = {}
    for product_id, qty in totals.items():
        prod = product_repo.get(conn, product_id)
        if prod is None:
            raise HTTPException(status_code=404, detail="product not found")
        products[product_id] = prod
        if prod["stock"] < qty:
            raise HTTPException(status_code=409, detail="insufficient stock")

    # Buraya gelindiyse tüm kontroller geçti — atomik uygula.
    snap_items = [
        {
            "product_id": it["product_id"],
            "quantity": it["quantity"],
            "unit_price_cents": products[it["product_id"]]["price_cents"],
        }
        for it in raw_items
    ]
    order_id = order_repo.create(conn, snap_items)
    for product_id, qty in totals.items():
        conn.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ?", (qty, product_id)
        )
    conn.commit()
    return _serialize(conn, order_repo.get(conn, order_id))


def get_order(conn: sqlite3.Connection, order_id: int) -> dict:
    order = order_repo.get(conn, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return _serialize(conn, order)


def cancel_order(conn: sqlite3.Connection, order_id: int) -> dict:
    order = order_repo.get(conn, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order["status"] == "cancelled":
        raise HTTPException(status_code=409, detail="order already cancelled")

    # Stokları geri yükle (idempotency: yalnızca ilk iptalde).
    for it in order_repo.get_items(conn, order_id):
        conn.execute(
            "UPDATE products SET stock = stock + ? WHERE id = ?",
            (it["quantity"], it["product_id"]),
        )
    order_repo.set_status(conn, order_id, "cancelled")
    conn.commit()
    return _serialize(conn, order_repo.get(conn, order_id))


def revenue_by_category(conn: sqlite3.Connection) -> dict:
    return order_repo.revenue_by_category(conn)
