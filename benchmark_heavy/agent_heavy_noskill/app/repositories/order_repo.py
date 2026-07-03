"""Order veri erişim katmanı — conn alır, ham satır/dict döndürür."""
import sqlite3

from app.models import order as order_model


def create(conn: sqlite3.Connection, items: list) -> dict:
    """items: [{product_id, quantity, unit_price_cents}, ...]"""
    cur = conn.execute("INSERT INTO orders (status) VALUES ('pending')")
    order_id = cur.lastrowid
    for it in items:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents) "
            "VALUES (?, ?, ?, ?)",
            (order_id, it["product_id"], it["quantity"], it["unit_price_cents"]),
        )
    conn.commit()
    return get(conn, order_id)


def get(conn: sqlite3.Connection, order_id: int):
    order_row = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if order_row is None:
        return None
    item_rows = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)
    ).fetchall()
    return order_model.to_dict(order_row, item_rows)


def set_status(conn: sqlite3.Connection, order_id: int, status: str) -> None:
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()


def count_items_for_product(conn: sqlite3.Connection, product_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM order_items WHERE product_id = ?", (product_id,)
    ).fetchone()
    return row["c"]


def revenue_by_category(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        """
        SELECT p.category AS category,
               SUM(oi.quantity * oi.unit_price_cents) AS revenue
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        JOIN products p ON p.id = oi.product_id
        WHERE o.status != 'cancelled'
        GROUP BY p.category
        """
    ).fetchall()
    return {r["category"]: r["revenue"] for r in rows}
