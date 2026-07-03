"""Order iş mantığı — domain kuralları, HTTPException fırlatır."""
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException

from app.repositories import order_repo, product_repo


def create_order(conn: sqlite3.Connection, data: dict) -> dict:
    raw_items = data["items"]  # şema boş/quantity<=0'ı 422 ile elemiştir

    # Aynı ürünün çoklu satırdaki toplam miktarını hesapla (atomik stok kontrolü).
    totals = defaultdict(int)
    for it in raw_items:
        totals[it["product_id"]] += it["quantity"]

    # Tüm ürünleri çek + 404 + toplam stok kontrolü (kısmi düşüm olmadan önce).
    products = {}
    for pid, qty in totals.items():
        prod = product_repo.get(conn, pid)
        if prod is None:
            raise HTTPException(status_code=404, detail=f"product {pid} not found")
        products[pid] = prod
        if prod["stock"] < qty:
            raise HTTPException(
                status_code=409, detail=f"insufficient stock for product {pid}"
            )

    # Snapshot fiyatlarıyla satırları kur.
    items = [
        {
            "product_id": it["product_id"],
            "quantity": it["quantity"],
            "unit_price_cents": products[it["product_id"]]["price_cents"],
        }
        for it in raw_items
    ]

    # Tek transaction: stok düş + sipariş yaz, sonra commit.
    try:
        order_id = order_repo.create(conn, _now(), items)
        for pid, qty in totals.items():
            conn.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?", (qty, pid)
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return order_repo.get(conn, order_id)


def get_order(conn: sqlite3.Connection, order_id: int) -> dict:
    order = order_repo.get(conn, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order


def cancel_order(conn: sqlite3.Connection, order_id: int) -> dict:
    order = get_order(conn, order_id)
    if order["status"] == "cancelled":
        raise HTTPException(status_code=409, detail="order already cancelled")

    try:
        for item in order_repo.get_items(conn, order_id):
            conn.execute(
                "UPDATE products SET stock = stock + ? WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )
        order_repo.set_status(conn, order_id, "cancelled")
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return order_repo.get(conn, order_id)


def revenue_by_category(conn: sqlite3.Connection) -> dict:
    return order_repo.revenue_by_category(conn)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
