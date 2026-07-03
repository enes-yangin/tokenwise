"""Order veri erişim katmanı — conn alır, ham satır/dict döndürür."""
import sqlite3
from datetime import datetime, timezone

from app.models import order as order_model


def create(conn: sqlite3.Connection, total_cents: int, items: list) -> dict:
    """Order oluştur ve items ekle. items = [{"product_id", "quantity", "unit_price_cents"}]"""
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
    return get(conn, order_id)


def get(conn: sqlite3.Connection, order_id: int) -> dict:
    """Order'ı items ile döndür."""
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not row:
        return None

    order = order_model.to_dict(row)
    items_rows = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
    ).fetchall()
    order["items"] = [order_model.order_item_to_dict(r) for r in items_rows]
    return order


def list_all(conn: sqlite3.Connection, limit=50, offset=0) -> list:
    """Tüm order'ları listele."""
    rows = conn.execute(
        "SELECT * FROM orders ORDER BY id LIMIT ? OFFSET ?", (limit, offset)
    ).fetchall()
    result = []
    for row in rows:
        order = order_model.to_dict(row)
        items_rows = conn.execute(
            "SELECT * FROM order_items WHERE order_id = ?", (row["id"],)
        ).fetchall()
        order["items"] = [order_model.order_item_to_dict(r) for r in items_rows]
        result.append(order)
    return result


def update_status(conn: sqlite3.Connection, order_id: int, status: str) -> dict:
    """Order status'ını güncelle."""
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    return get(conn, order_id)


def product_is_referenced(conn: sqlite3.Connection, product_id: int) -> bool:
    """Bu ürün herhangi bir order_items satırında referanslı mı?"""
    row = conn.execute(
        "SELECT 1 FROM order_items WHERE product_id = ? LIMIT 1", (product_id,)
    ).fetchone()
    return row is not None


def get_revenue_by_category(conn: sqlite3.Connection) -> dict:
    """Kategori bazında toplam gelir (cents) döndür."""
    rows = conn.execute(
        """
        SELECT p.category, SUM(oi.unit_price_cents * oi.quantity) as total
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status = 'pending'
        GROUP BY p.category
        """
    ).fetchall()
    return {row["category"]: row["total"] for row in rows}
