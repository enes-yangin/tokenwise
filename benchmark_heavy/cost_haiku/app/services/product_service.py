"""Product iş mantığı — domain kuralları, HTTPException fırlatır."""
import sqlite3

from fastapi import HTTPException

from app.repositories import product_repo


def create_product(conn: sqlite3.Connection, data: dict) -> dict:
    if product_repo.get_by_sku(conn, data["sku"]):
        raise HTTPException(status_code=409, detail="sku already exists")
    return product_repo.create(conn, data)


def get_product(conn: sqlite3.Connection, product_id: int) -> dict:
    prod = product_repo.get(conn, product_id)
    if prod is None:
        raise HTTPException(status_code=404, detail="product not found")
    return prod


def list_products(conn, category=None, limit=50, offset=0) -> list:
    return product_repo.list_(conn, category, limit, offset)


def update_product(conn: sqlite3.Connection, product_id: int, fields: dict) -> dict:
    get_product(conn, product_id)  # 404 kontrolü
    if "sku" in fields:
        other = product_repo.get_by_sku(conn, fields["sku"])
        if other and other["id"] != product_id:
            raise HTTPException(status_code=409, detail="sku already exists")
    return product_repo.update(conn, product_id, fields)


def delete_product(conn: sqlite3.Connection, product_id: int) -> None:
    get_product(conn, product_id)  # 404 kontrolü
    # Referential integrity: check if product has orders
    order_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM order_items WHERE product_id = ?",
        (product_id,)
    ).fetchone()
    if order_count and order_count["cnt"] > 0:
        raise HTTPException(status_code=409, detail="product has orders")
    product_repo.delete(conn, product_id)
