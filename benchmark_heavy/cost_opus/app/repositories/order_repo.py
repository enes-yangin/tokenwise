"""Order veri erişim katmanı — conn alır, dict döndürür."""
import sqlite3

from app.models import order as order_model


def create(conn: sqlite3.Connection, created_at: str, items: list) -> dict:
    """items: [{"product_id", "quantity", "unit_price_cents"}]. Tek transaction."""
    cur = conn.execute(
        "INSERT INTO orders (status, created_at) VALUES ('pending', ?)",
        (created_at,),
    )
    order_id = cur.lastrowid
    for it in items:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents) "
            "VALUES (?, ?, ?, ?)",
            (order_id, it["product_id"], it["quantity"], it["unit_price_cents"]),
        )
    return order_id


def get(conn: sqlite3.Connection, order_id: int):
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        return None
    items = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)
    ).fetchall()
    return order_model.to_dict(row, items)


def get_items(conn: sqlite3.Connection, order_id: int) -> list:
    rows = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def set_status(conn: sqlite3.Connection, order_id: int, status: str) -> None:
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))


def product_referenced(conn: sqlite3.Connection, product_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM order_items WHERE product_id = ? LIMIT 1", (product_id,)
    ).fetchone()
    return row is not None


def revenue_by_category(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        "SELECT p.category AS category, "
        "SUM(oi.quantity * oi.unit_price_cents) AS total "
        "FROM order_items oi "
        "JOIN orders o ON o.id = oi.order_id "
        "JOIN products p ON p.id = oi.product_id "
        "WHERE o.status != 'cancelled' "
        "GROUP BY p.category"
    ).fetchall()
    return {r["category"]: r["total"] for r in rows}
