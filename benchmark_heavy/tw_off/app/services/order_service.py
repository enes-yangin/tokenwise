"""Order iş mantığı — domain kuralları, HTTPException fırlatır."""
import sqlite3
from collections import OrderedDict

from fastapi import HTTPException

from app.repositories import order_repo, product_repo


def create_order(conn: sqlite3.Connection, items: list) -> dict:
    """items: [{"product_id": int, "quantity": int}, ...]"""
    # Aynı ürün birden çok satırda ise toplam miktarı topla.
    totals: "OrderedDict[int, int]" = OrderedDict()
    for item in items:
        totals[item["product_id"]] = totals.get(item["product_id"], 0) + item["quantity"]

    products = {}
    for product_id, qty in totals.items():
        product = product_repo.get(conn, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="product not found")
        if product["stock"] < qty:
            raise HTTPException(status_code=409, detail="insufficient stock")
        products[product_id] = product

    # Tüm kontroller geçti -> atomik olarak stok düş + order oluştur.
    order_items = [
        {
            "product_id": item["product_id"],
            "quantity": item["quantity"],
            "unit_price_cents": products[item["product_id"]]["price_cents"],
        }
        for item in items
    ]
    for product_id, qty in totals.items():
        product_repo.adjust_stock(conn, product_id, -qty)

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
    return order_repo.get(conn, order_id)


def revenue_by_category(conn: sqlite3.Connection) -> dict:
    return order_repo.revenue_by_category(conn)
