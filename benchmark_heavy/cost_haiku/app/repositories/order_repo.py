"""Order veri erişim katmanı — conn alır, ham satır/dict döndürür."""
import sqlite3

from app.models import order as order_model


def create(conn: sqlite3.Connection, total_cents: int, items_data: list) -> dict:
    """Create order and items, return full order with items."""
    cur = conn.execute(
        "INSERT INTO orders (status, total_cents) VALUES (?, ?)",
        ("pending", total_cents),
    )
    order_id = cur.lastrowid

    for item in items_data:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents) "
            "VALUES (?, ?, ?, ?)",
            (order_id, item["product_id"], item["quantity"], item["unit_price_cents"]),
        )

    conn.commit()
    return get(conn, order_id)


def get(conn: sqlite3.Connection, order_id: int) -> dict:
    row = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if not row:
        return None

    items_rows = conn.execute(
        "SELECT product_id, quantity, unit_price_cents FROM order_items WHERE order_id = ? "
        "ORDER BY id",
        (order_id,),
    ).fetchall()
    items = [order_model.item_to_dict(r) for r in items_rows]

    return order_model.to_dict(row, items)


def update_status(conn: sqlite3.Connection, order_id: int, new_status: str) -> dict:
    conn.execute(
        "UPDATE orders SET status = ? WHERE id = ?",
        (new_status, order_id),
    )
    conn.commit()
    return get(conn, order_id)


def get_all_active_items(conn: sqlite3.Connection) -> list:
    """Get all order items from non-cancelled orders for revenue calculation."""
    rows = conn.execute(
        """SELECT oi.product_id, oi.quantity, oi.unit_price_cents, p.category
           FROM order_items oi
           JOIN orders o ON oi.order_id = o.id
           JOIN products p ON oi.product_id = p.id
           WHERE o.status != 'cancelled'
           ORDER BY oi.id"""
    ).fetchall()
    return [{"product_id": r["product_id"], "quantity": r["quantity"],
             "unit_price_cents": r["unit_price_cents"], "category": r["category"]}
            for r in rows]
