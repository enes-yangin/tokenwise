"""Product veri erişim katmanı — conn alır, ham satır/dict döndürür."""
import sqlite3

from app.models import product as product_model


def create(conn: sqlite3.Connection, data: dict) -> dict:
    cur = conn.execute(
        "INSERT INTO products (name, sku, price_cents, stock, category) "
        "VALUES (?, ?, ?, ?, ?)",
        (data["name"], data["sku"], data["price_cents"], data["stock"], data["category"]),
    )
    conn.commit()
    return get(conn, cur.lastrowid)


def get(conn: sqlite3.Connection, product_id: int):
    row = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    return product_model.to_dict(row) if row else None


def get_by_sku(conn: sqlite3.Connection, sku: str):
    row = conn.execute("SELECT * FROM products WHERE sku = ?", (sku,)).fetchone()
    return product_model.to_dict(row) if row else None


def is_referenced_by_order_items(conn: sqlite3.Connection, product_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM order_items WHERE product_id = ? LIMIT 1", (product_id,)
    ).fetchone()
    return row is not None


def list_(conn: sqlite3.Connection, category=None, limit=50, offset=0) -> list:
    if category is not None:
        rows = conn.execute(
            "SELECT * FROM products WHERE category = ? ORDER BY id LIMIT ? OFFSET ?",
            (category, limit, offset),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM products ORDER BY id LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
    return [product_model.to_dict(r) for r in rows]


def update(conn: sqlite3.Connection, product_id: int, fields: dict) -> dict:
    if fields:
        cols = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE products SET {cols} WHERE id = ?",
            (*fields.values(), product_id),
        )
        conn.commit()
    return get(conn, product_id)


def delete(conn: sqlite3.Connection, product_id: int) -> None:
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()


def adjust_stock(conn: sqlite3.Connection, product_id: int, delta: int) -> None:
    conn.execute(
        "UPDATE products SET stock = stock + ? WHERE id = ?", (delta, product_id)
    )
    conn.commit()
