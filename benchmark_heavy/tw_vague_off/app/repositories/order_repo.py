"""Order veri erişim katmanı — conn alır, ham satır/dict döndürür."""
import sqlite3
from datetime import datetime, timezone

from app.models import order as order_model


def create(conn: sqlite3.Connection, items: list) -> dict:
    """items: [{"product_id", "quantity", "unit_price_cents"}, ...]"""
    total_cents = sum(i["quantity"] * i["unit_price_cents"] for i in items)
    created_at = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO orders (status, created_at, total_cents) VALUES (?, ?, ?)",
        ("created", created_at, total_cents),
    )
    order_id = cur.lastrowid
    for i in items:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents) "
            "VALUES (?, ?, ?, ?)",
            (order_id, i["product_id"], i["quantity"], i["unit_price_cents"]),
        )
    conn.commit()
    return get(conn, order_id)


def get(conn: sqlite3.Connection, order_id: int):
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        return None
    item_rows = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)
    ).fetchall()
    items = [order_model.item_to_dict(r) for r in item_rows]
    return order_model.to_dict(row, items)


def set_status(conn: sqlite3.Connection, order_id: int, status: str) -> None:
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()


def get_items(conn: sqlite3.Connection, order_id: int) -> list:
    rows = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)
    ).fetchall()
    return [order_model.item_to_dict(r) for r in rows]


def revenue_by_category(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        """
        SELECT p.category AS category, SUM(oi.quantity * oi.unit_price_cents) AS total
        FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        JOIN orders o ON o.id = oi.order_id
        WHERE o.status != 'cancelled'
        GROUP BY p.category
        """
    ).fetchall()
    return {row["category"]: row["total"] for row in rows}
