"""Order veri erişim katmanı — conn alır, ham satır/dict döndürür."""
import sqlite3
from datetime import datetime, timezone

from app.models import order as order_model


def create(conn: sqlite3.Connection, items: list) -> dict:
    """items: [{"product_id", "quantity", "unit_price_cents"}, ...]"""
    created_at = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO orders (status, created_at) VALUES (?, ?)",
        ("pending", created_at),
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


def get(conn: sqlite3.Connection, order_id: int):
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        return None
    items = get_items(conn, order_id)
    return order_model.to_dict(row, items)


def get_items(conn: sqlite3.Connection, order_id: int) -> list:
    rows = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
    ).fetchall()
    return [order_model.item_to_dict(r) for r in rows]


def set_status(conn: sqlite3.Connection, order_id: int, status: str) -> None:
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()


def count_referencing_product(conn: sqlite3.Connection, product_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM order_items WHERE product_id = ?", (product_id,)
    ).fetchone()
    return row["c"]


def revenue_by_category(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        """
        SELECT p.category AS category, SUM(oi.quantity * oi.unit_price_cents) AS total
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        JOIN products p ON p.id = oi.product_id
        WHERE o.status != 'cancelled'
        GROUP BY p.category
        """
    ).fetchall()
    return {r["category"]: r["total"] for r in rows}
