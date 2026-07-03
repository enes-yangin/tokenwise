"""Order veri erişim katmanı — conn alır, ham satır/dict döndürür."""
import sqlite3
from datetime import datetime, timezone

from app.models import order as order_model


def create(conn: sqlite3.Connection, items: list) -> int:
    """Yeni bir sipariş oluştur ve order_id döndür.

    items: [{"product_id": int, "quantity": int, "unit_price_cents": int}, ...]
    """
    total_cents = sum(item["unit_price_cents"] * item["quantity"] for item in items)
    created_at = datetime.now(timezone.utc).isoformat()

    cur = conn.execute(
        "INSERT INTO orders (status, created_at, total_cents) VALUES (?, ?, ?)",
        ("pending", created_at, total_cents),
    )
    order_id = cur.lastrowid

    for item in items:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents) "
            "VALUES (?, ?, ?, ?)",
            (order_id, item["product_id"], item["quantity"], item["unit_price_cents"]),
        )

    conn.commit()
    return order_id


def get(conn: sqlite3.Connection, order_id: int) -> dict:
    """Sipariş ve itemlerini döndür."""
    row = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()

    if not row:
        return None

    order = order_model.to_dict(row)

    items_rows = conn.execute(
        "SELECT product_id, quantity, unit_price_cents FROM order_items WHERE order_id = ?",
        (order_id,),
    ).fetchall()

    order["items"] = [order_model.item_to_dict(r) for r in items_rows]

    return order


def update_status(conn: sqlite3.Connection, order_id: int, status: str) -> dict:
    """Sipariş statusunu güncelle."""
    conn.execute(
        "UPDATE orders SET status = ? WHERE id = ?",
        (status, order_id),
    )
    conn.commit()
    return get(conn, order_id)


def get_revenue_by_category(conn: sqlite3.Connection) -> dict:
    """Kategori başına toplam gelir döndür (sadece pending/confirmed siparişler)."""
    rows = conn.execute(
        """
        SELECT p.category, SUM(oi.unit_price_cents * oi.quantity) as total_cents
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status IN ('pending', 'confirmed')
        GROUP BY p.category
        """
    ).fetchall()

    return {row["category"]: row["total_cents"] for row in rows}
