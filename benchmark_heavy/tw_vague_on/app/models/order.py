"""Order modeli — şema + satır serileştirme."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    total_cents INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price_cents INTEGER NOT NULL
);
"""


def to_dict(row: sqlite3.Row, items: list) -> dict:
    return {
        "id": row["id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "items": items,
        "total_cents": row["total_cents"],
    }


def item_to_dict(row: sqlite3.Row) -> dict:
    return {
        "product_id": row["product_id"],
        "quantity": row["quantity"],
        "unit_price_cents": row["unit_price_cents"],
    }
