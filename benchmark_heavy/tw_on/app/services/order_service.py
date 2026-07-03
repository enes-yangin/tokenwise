"""Order iş mantığı — domain kuralları, HTTPException fırlatır."""
import sqlite3
from collections import defaultdict

from fastapi import HTTPException

from app.repositories import order_repo, product_repo


def create_order(conn: sqlite3.Connection, items: list) -> dict:
    """items: [{"product_id", "quantity"}, ...] — pydantic ile quantity>0 ve items non-empty garanti."""
    # aynı ürün birden çok satırda ise toplam miktarı topla
    qty_by_product: dict = defaultdict(int)
    order_lines = []  # (product_id, quantity) orijinal sırayla
    for it in items:
        qty_by_product[it["product_id"]] += it["quantity"]
        order_lines.append((it["product_id"], it["quantity"]))

    # ürünleri yükle + 404 / stok kontrolü (atomik: hiçbir şey yazmadan önce doğrula)
    products_by_id = {}
    for product_id in qty_by_product:
        prod = product_repo.get(conn, product_id)
        if prod is None:
            raise HTTPException(status_code=404, detail="product not found")
        products_by_id[product_id] = prod

    for product_id, total_qty in qty_by_product.items():
        if products_by_id[product_id]["stock"] < total_qty:
            raise HTTPException(status_code=409, detail="insufficient stock")

    # doğrulama geçti: stok düş + fiyatı snapshot'la
    order_items = [
        {
            "product_id": product_id,
            "quantity": quantity,
            "unit_price_cents": products_by_id[product_id]["price_cents"],
        }
        for product_id, quantity in order_lines
    ]
    for product_id, total_qty in qty_by_product.items():
        product_repo.adjust_stock(conn, product_id, -total_qty)

    return order_repo.create(conn, order_items)


def get_order(conn: sqlite3.Connection, order_id: int) -> dict:
    order = order_repo.get(conn, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order


def cancel_order(conn: sqlite3.Connection, order_id: int) -> dict:
    order = get_order(conn, order_id)
    if order["status"] == "cancelled":
        raise HTTPException(status_code=409, detail="order already cancelled")
    for item in order["items"]:
        product_repo.adjust_stock(conn, item["product_id"], item["quantity"])
    order_repo.set_status(conn, order_id, "cancelled")
    return get_order(conn, order_id)


def revenue_by_category(conn: sqlite3.Connection) -> dict:
    return order_repo.revenue_by_category(conn)
