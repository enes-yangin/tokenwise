"""Order iş mantığı — domain kuralları, HTTPException fırlatır.

Sipariş oluşturma: ürünlerin varlığı ve stok yeterliliği kontrol edilir,
sipariş anındaki fiyat dondurulur, ilgili ürünlerin stoğu düşürülür.
İptal: yalnızca 'created' siparişler iptal edilebilir, stok geri yüklenir.
"""
import sqlite3
from datetime import datetime, timezone

from fastapi import HTTPException

from app.repositories import order_repo, product_repo

STATUS_CREATED = "created"
STATUS_CANCELLED = "cancelled"


def create_order(conn: sqlite3.Connection, data: dict) -> dict:
    items = data["items"]

    # Aynı ürün birden çok kez gelebilir; toplam adedi birleştir.
    quantities: dict = {}
    for item in items:
        quantities[item["product_id"]] = (
            quantities.get(item["product_id"], 0) + item["quantity"]
        )

    resolved = []
    for product_id, quantity in quantities.items():
        product = product_repo.get(conn, product_id)
        if product is None:
            raise HTTPException(
                status_code=404, detail=f"product {product_id} not found"
            )
        if product["stock"] < quantity:
            raise HTTPException(
                status_code=409,
                detail=f"insufficient stock for product {product_id}",
            )
        resolved.append(
            {
                "product_id": product_id,
                "quantity": quantity,
                "unit_price_cents": product["price_cents"],
                "category": product["category"],
            }
        )

    created_at = datetime.now(timezone.utc).isoformat()
    order = order_repo.create(conn, STATUS_CREATED, created_at, resolved)

    for item in resolved:
        product_repo.adjust_stock(conn, item["product_id"], -item["quantity"])

    return order


def get_order(conn: sqlite3.Connection, order_id: int) -> dict:
    order = order_repo.get(conn, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order


def cancel_order(conn: sqlite3.Connection, order_id: int) -> dict:
    order = get_order(conn, order_id)
    if order["status"] == STATUS_CANCELLED:
        raise HTTPException(status_code=409, detail="order already cancelled")

    for item in order["items"]:
        product_repo.adjust_stock(conn, item["product_id"], item["quantity"])

    return order_repo.set_status(conn, order_id, STATUS_CANCELLED)


def revenue_by_category(conn: sqlite3.Connection) -> dict:
    return order_repo.revenue_by_category(conn)
