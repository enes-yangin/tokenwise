"""Order veri erişim katmanı — conn alır, ham dict döndürür."""
import sqlite3

from app.models import order as order_model


def create(conn: sqlite3.Connection, status: str, created_at: str, items: list) -> dict:
    cur = conn.execute(
        "INSERT INTO orders (status, created_at) VALUES (?, ?)",
        (status, created_at),
    )
    order_id = cur.lastrowid
    for item in items:
        conn.execute(
            "INSERT INTO order_items "
            "(order_id, product_id, quantity, unit_price_cents, category) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                order_id,
                item["product_id"],
                item["quantity"],
                item["unit_price_cents"],
                item["category"],
            ),
        )
    conn.commit()
    return get(conn, order_id)


def _items(conn: sqlite3.Connection, order_id: int) -> list:
    return conn.execute(
        "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)
    ).fetchall()


def get(conn: sqlite3.Connection, order_id: int):
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        return None
    return order_model.to_dict(row, _items(conn, order_id))


def set_status(conn: sqlite3.Connection, order_id: int, status: str) -> dict:
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    return get(conn, order_id)


def revenue_by_category(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        "SELECT oi.category AS category, "
        "SUM(oi.quantity * oi.unit_price_cents) AS total "
        "FROM order_items oi "
        "JOIN orders o ON o.id = oi.order_id "
        "WHERE o.status = 'created' "
        "GROUP BY oi.category"
    ).fetchall()
    return {r["category"]: r["total"] for r in rows}
