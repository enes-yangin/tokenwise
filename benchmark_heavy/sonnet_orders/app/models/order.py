"""Order modeli — şema + satır serileştirme."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price_cents INTEGER NOT NULL
);
"""


def to_dict(order_row: sqlite3.Row, item_rows: list) -> dict:
    items = [
        {
            "product_id": r["product_id"],
            "quantity": r["quantity"],
            "unit_price_cents": r["unit_price_cents"],
        }
        for r in item_rows
    ]
    total_cents = sum(i["quantity"] * i["unit_price_cents"] for i in items)
    return {
        "id": order_row["id"],
        "status": order_row["status"],
        "created_at": order_row["created_at"],
        "items": items,
        "total_cents": total_cents,
    }
