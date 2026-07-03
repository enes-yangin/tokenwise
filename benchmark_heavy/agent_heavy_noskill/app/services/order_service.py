"""Order iş mantığı — domain kuralları, HTTPException fırlatır."""
import sqlite3

from fastapi import HTTPException

from app.repositories import order_repo, product_repo


def create_order(conn: sqlite3.Connection, items: list) -> dict:
    """items: [{product_id, quantity}, ...] (pydantic doğrulanmış: quantity>0, items boş değil)."""
    # Aynı ürün birden çok satırda → toplam miktar.
    totals: dict = {}
    order_in_lines = []
    for it in items:
        pid = it["product_id"]
        qty = it["quantity"]
        totals[pid] = totals.get(pid, 0) + qty
        order_in_lines.append((pid, qty))

    # Ürünleri çöz + 404 + fiyat snapshot.
    products: dict = {}
    for pid in totals:
        prod = product_repo.get(conn, pid)
        if prod is None:
            raise HTTPException(status_code=404, detail=f"product {pid} not found")
        products[pid] = prod

    # Atomik stok kontrolü (toplam miktar üzerinden) — hiçbir düşüm yapmadan önce.
    for pid, total_qty in totals.items():
        if products[pid]["stock"] < total_qty:
            raise HTTPException(
                status_code=409, detail=f"insufficient stock for product {pid}"
            )

    # Tüm kontroller geçti → stok düş + sipariş kalemleri (snapshot fiyat).
    for pid, total_qty in totals.items():
        product_repo.adjust_stock(conn, pid, -total_qty)

    item_rows = [
        {
            "product_id": pid,
            "quantity": qty,
            "unit_price_cents": products[pid]["price_cents"],
        }
        for pid, qty in order_in_lines
    ]
    return order_repo.create(conn, item_rows)


def get_order(conn: sqlite3.Connection, order_id: int) -> dict:
    order = order_repo.get(conn, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order


def cancel_order(conn: sqlite3.Connection, order_id: int) -> dict:
    order = get_order(conn, order_id)  # 404 kontrolü
    if order["status"] == "cancelled":
        raise HTTPException(status_code=409, detail="order already cancelled")
    # Stokları geri yükle.
    for item in order["items"]:
        product_repo.adjust_stock(conn, item["product_id"], item["quantity"])
    order_repo.set_status(conn, order_id, "cancelled")
    return order_repo.get(conn, order_id)


def revenue_by_category(conn: sqlite3.Connection) -> dict:
    return order_repo.revenue_by_category(conn)
