"""Order iş mantığı — domain kuralları, HTTPException fırlatır."""
import sqlite3
from collections import defaultdict

from fastapi import HTTPException

from app.repositories import order_repo, product_repo


def create_order(conn: sqlite3.Connection, items: list) -> dict:
    """
    items: [{"product_id": int, "quantity": int}]
    Atomik stok düşümü: tüm ürünler varsa ve stok yeterliyse commit, aksi hâlde 409.
    Aynı product_id birden fazla satırda gelirse toplamı kontrol et.
    """
    # Toplam miktarları product_id bazında birleştir
    aggregated: dict[int, int] = defaultdict(int)
    for item in items:
        aggregated[item["product_id"]] += item["quantity"]

    # Ürünleri al ve stok kontrolü yap
    products = {}
    for product_id, qty in aggregated.items():
        prod = product_repo.get(conn, product_id)
        if prod is None:
            raise HTTPException(status_code=404, detail=f"product {product_id} not found")
        if prod["stock"] < qty:
            raise HTTPException(status_code=409, detail=f"insufficient stock for product {product_id}")
        products[product_id] = prod

    # Atomik stok düşümü
    for product_id, qty in aggregated.items():
        product_repo.adjust_stock(conn, product_id, -qty)

    # Sipariş oluştur — orijinal satır sırası, snapshot fiyatıyla
    order_items = [
        {
            "product_id": item["product_id"],
            "quantity": item["quantity"],
            "unit_price_cents": products[item["product_id"]]["price_cents"],
        }
        for item in items
    ]

    return order_repo.create(conn, order_items)


def get_order(conn: sqlite3.Connection, order_id: int) -> dict:
    order = order_repo.get(conn, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order


def cancel_order(conn: sqlite3.Connection, order_id: int) -> dict:
    order = get_order(conn, order_id)
    if order["status"] == "cancelled":
        raise HTTPException(status_code=409, detail="order already cancelled")
    # Stokları geri yükle
    for item in order["items"]:
        product_repo.adjust_stock(conn, item["product_id"], item["quantity"])
    order_repo.set_status(conn, order_id, "cancelled")
    return get_order(conn, order_id)


def revenue_by_category(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        """
        SELECT p.category, SUM(oi.quantity * oi.unit_price_cents) AS total
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        JOIN products p ON oi.product_id = p.id
        WHERE o.status != 'cancelled'
        GROUP BY p.category
        """
    ).fetchall()
    return {row["category"]: row["total"] for row in rows}
