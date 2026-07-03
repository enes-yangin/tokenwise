"""Order modeli — şema + satır serileştirme."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    total_cents INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
"""


def to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "total_cents": row["total_cents"],
    }


def item_to_dict(row: sqlite3.Row) -> dict:
    return {
        "product_id": row["product_id"],
        "quantity": row["quantity"],
        "unit_price_cents": row["unit_price_cents"],
    }
