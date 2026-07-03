"""Order veri erişim katmanı."""
import sqlite3

from app.models import order as order_model


def get(conn: sqlite3.Connection, order_id: int):
    order_row = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if order_row is None:
        return None
    item_rows = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
    ).fetchall()
    return order_model.to_dict(order_row, item_rows)


def create(conn: sqlite3.Connection, items: list) -> dict:
    """items: [{"product_id": int, "quantity": int, "unit_price_cents": int}]"""
    cur = conn.execute(
        "INSERT INTO orders (status) VALUES ('pending')"
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


def set_status(conn: sqlite3.Connection, order_id: int, status: str) -> None:
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()


def has_product_reference(conn: sqlite3.Connection, product_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM order_items WHERE product_id = ? LIMIT 1", (product_id,)
    ).fetchone()
    return row is not None
