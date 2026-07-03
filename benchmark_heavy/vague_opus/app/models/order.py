"""Order modeli — şema + satır serileştirme.

Bir sipariş (orders) ve onun kalemleri (order_items) iki tabloda tutulur.
unit_price_cents, sipariş anındaki ürün fiyatını dondurur (fiyat sonradan
değişse bile sipariş tutarı sabit kalır).
"""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    category TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
"""


def item_to_dict(row: sqlite3.Row) -> dict:
    return {
        "product_id": row["product_id"],
        "quantity": row["quantity"],
        "unit_price_cents": row["unit_price_cents"],
    }


def to_dict(row: sqlite3.Row, items: list) -> dict:
    return {
        "id": row["id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "items": [item_to_dict(i) for i in items],
        "total_cents": sum(i["quantity"] * i["unit_price_cents"] for i in items),
    }
