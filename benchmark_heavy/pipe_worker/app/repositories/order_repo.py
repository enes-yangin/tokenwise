"""Order veri erişim katmanı — conn alır, ham satır/dict döndürür."""
import sqlite3
from datetime import datetime, timezone

from app.models import order as order_model


def create(conn: sqlite3.Connection) -> dict:
    """Yeni order oluştur, id ile döner."""
    created_at = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO orders (status, created_at) VALUES (?, ?)",
        ("active", created_at),
    )
    conn.commit()
    return get(conn, cur.lastrowid)


def get(conn: sqlite3.Connection, order_id: int) -> dict:
    """Order ve kalemlerini döner, yoksa None."""
    row = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if row is None:
        return None

    order = order_model.to_dict(row)

    # Kalemler
    item_rows = conn.execute(
        "SELECT product_id, quantity, unit_price_cents FROM order_items "
        "WHERE order_id = ? ORDER BY id ASC",
        (order_id,),
    ).fetchall()

    items = [order_model.item_to_dict(r) for r in item_rows]
    total_cents = sum(item["quantity"] * item["unit_price_cents"] for item in items)

    order["items"] = items
    order["total_cents"] = total_cents
    return order


def add_item(conn: sqlite3.Connection, order_id: int, product_id: int,
             quantity: int, unit_price_cents: int) -> None:
    """Order'a kalem ekle."""
    conn.execute(
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents) "
        "VALUES (?, ?, ?, ?)",
        (order_id, product_id, quantity, unit_price_cents),
    )


def update_status(conn: sqlite3.Connection, order_id: int, status: str) -> None:
    """Order statüsünü güncelle."""
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()


def get_items(conn: sqlite3.Connection, order_id: int) -> list:
    """Order'ın kalemlerini döner."""
    rows = conn.execute(
        "SELECT product_id, quantity, unit_price_cents FROM order_items "
        "WHERE order_id = ? ORDER BY id ASC",
        (order_id,),
    ).fetchall()
    return [order_model.item_to_dict(r) for r in rows]
