"""Product modeli — şema + satır serileştirme."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sku TEXT NOT NULL UNIQUE,
    price_cents INTEGER NOT NULL,
    stock INTEGER NOT NULL,
    category TEXT NOT NULL
);
"""


def to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "sku": row["sku"],
        "price_cents": row["price_cents"],
        "stock": row["stock"],
        "category": row["category"],
    }
