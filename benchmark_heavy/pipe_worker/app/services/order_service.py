"""Order iş mantığı — domain kuralları, HTTPException fırlatır."""
import sqlite3

from fastapi import HTTPException

from app.repositories import order_repo, product_repo


def create_order(conn: sqlite3.Connection, order_in: dict) -> dict:
    """
    Sipariş oluştur: kalemler birleştirilir, stok all-or-nothing, snapshot yazılır.
    """
    # 1. Kalemler product_id'ye göre birleştirilir
    merged = {}
    for item in order_in["items"]:
        pid = item["product_id"]
        qty = item["quantity"]
        if pid in merged:
            merged[pid] += qty
        else:
            merged[pid] = qty

    # 2. Tüm product_id'ler var mı ve stok yeterli mi kontrol et (all-or-nothing)
    for product_id, total_qty in merged.items():
        product = product_repo.get(conn, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="product not found")
        if product["stock"] < total_qty:
            raise HTTPException(status_code=409, detail="insufficient stock")

    # 3. Stok düşür ve order yazıl
    order = order_repo.create(conn)
    try:
        for product_id, total_qty in merged.items():
            # Stok düşür
            product_repo.adjust_stock(conn, product_id, -total_qty)

            # Fiyat snapshot'ını al ve kalem yaz
            product = product_repo.get(conn, product_id)
            order_repo.add_item(
                conn, order["id"], product_id, total_qty, product["price_cents"]
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    # Güncel order döner (items + total_cents hesaplanır)
    return order_repo.get(conn, order["id"])


def get_order(conn: sqlite3.Connection, order_id: int) -> dict:
    """Order varsa döner, yoksa 404."""
    order = order_repo.get(conn, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order


def cancel_order(conn: sqlite3.Connection, order_id: int) -> dict:
    """
    Siparişi iptal et: active ise statüsü cancelled yap ve stok iade et.
    İdempotent: zaten cancelled ise 200 no-op.
    """
    order = order_repo.get(conn, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")

    # Zaten iptal edilmişse no-op
    if order["status"] == "cancelled":
        return order

    # Statüsü iptal yap
    order_repo.update_status(conn, order_id, "cancelled")

    # Kalemler için stok iade et
    items = order_repo.get_items(conn, order_id)
    for item in items:
        product_id = item["product_id"]
        quantity = item["quantity"]

        # Ürün silinmişse iadesi atlan
        product = product_repo.get(conn, product_id)
        if product is not None:
            product_repo.adjust_stock(conn, product_id, quantity)

    conn.commit()

    # Güncel order döner
    return order_repo.get(conn, order_id)


def get_revenue_by_category(conn: sqlite3.Connection) -> dict:
    """
    Active siparişlerin kalemlerinden kategori bazında gelir.
    Snapshot fiyatı, canlı kategori, silinmiş ürün hariç.
    """
    rows = conn.execute("""
        SELECT
            p.category,
            oi.quantity,
            oi.unit_price_cents
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        LEFT JOIN products p ON oi.product_id = p.id
        WHERE o.status = 'active'
    """).fetchall()

    revenue = {}
    for row in rows:
        category = row[0]
        quantity = row[1]
        unit_price_cents = row[2]

        # Kategori null ise (ürün silinmişse) atla
        if category is None:
            continue

        revenue_cents = quantity * unit_price_cents
        revenue[category] = revenue.get(category, 0) + revenue_cents

    return revenue
