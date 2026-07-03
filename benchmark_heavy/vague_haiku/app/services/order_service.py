"""Order iş mantığı — domain kuralları, HTTPException fırlatır."""
import sqlite3

from fastapi import HTTPException

from app.repositories import order_repo, product_repo


def create_order(conn: sqlite3.Connection, items_data: list) -> dict:
    """
    Order oluştur: ürünleri kontrol et, stoğu düşür, order kaydet.
    items_data = [{"product_id": int, "quantity": int}, ...] or [OrderItemIn, ...]
    """
    # Ürünleri ve fiyatları kontrol et
    order_items = []
    total_cents = 0

    for item_data in items_data:
        # Handle both dict and pydantic model
        if hasattr(item_data, "model_dump"):
            product_id = item_data.product_id
            quantity = item_data.quantity
        else:
            product_id = item_data["product_id"]
            quantity = item_data["quantity"]

        product = product_repo.get(conn, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail=f"product {product_id} not found")

        if product["stock"] < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"insufficient stock for product {product_id}",
            )

        order_items.append(
            {
                "product_id": product_id,
                "quantity": quantity,
                "unit_price_cents": product["price_cents"],
            }
        )
        total_cents += product["price_cents"] * quantity

        # Stoğu hemen düşür
        product_repo.adjust_stock(conn, product_id, -quantity)

    # Order oluştur
    return order_repo.create(conn, total_cents, order_items)


def get_order(conn: sqlite3.Connection, order_id: int) -> dict:
    """Order'ı getir, bulunamazsa 404 fırlat."""
    order = order_repo.get(conn, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order


def cancel_order(conn: sqlite3.Connection, order_id: int) -> dict:
    """
    Order'ı iptal et: status'unu 'cancelled' yap, ürün stoğunu geri ver.
    Iptal edilmiş order zaten iptal edilemez.
    """
    order = get_order(conn, order_id)

    if order["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="order already cancelled")

    # Ürün stoğunu geri ver
    for item in order["items"]:
        product_repo.adjust_stock(conn, item["product_id"], item["quantity"])

    # Status'u güncelle
    return order_repo.update_status(conn, order_id, "cancelled")


def get_revenue_by_category(conn: sqlite3.Connection) -> dict:
    """Kategori bazında gelir raporu döndür (pending order'lar için)."""
    return order_repo.get_revenue_by_category(conn)
