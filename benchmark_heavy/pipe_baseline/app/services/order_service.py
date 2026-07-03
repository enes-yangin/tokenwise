"""Order iş mantığı — domain kuralları, HTTPException fırlatır."""
import sqlite3

from fastapi import HTTPException

from app.repositories import order_repo, product_repo


def create_order(conn: sqlite3.Connection, items: list) -> dict:
    """Yeni bir sipariş oluştur.

    1. Tüm ürünleri kontrol et (var ve stok yeterli)
    2. Fiyatları al
    3. Siparişi oluştur ve stoğu düşür
    """
    if not items:
        raise HTTPException(status_code=400, detail="items cannot be empty")

    # Tüm ürünleri ve fiyatları kontrol et
    order_items = []
    for item in items:
        # item pydantic object veya dict olabilir
        product_id = item.product_id if hasattr(item, 'product_id') else item["product_id"]
        quantity = item.quantity if hasattr(item, 'quantity') else item["quantity"]

        prod = product_repo.get(conn, product_id)
        if prod is None:
            raise HTTPException(
                status_code=404, detail=f"product {product_id} not found"
            )
        if prod["stock"] < quantity:
            raise HTTPException(
                status_code=409,
                detail=f"product {product_id} insufficient stock",
            )
        order_items.append(
            {
                "product_id": product_id,
                "quantity": quantity,
                "unit_price_cents": prod["price_cents"],
            }
        )

    # Siparişi oluştur
    order_id = order_repo.create(conn, order_items)

    # Stoğu düşür
    for item in order_items:
        product_repo.adjust_stock(conn, item["product_id"], -item["quantity"])

    return order_repo.get(conn, order_id)


def get_order(conn: sqlite3.Connection, order_id: int) -> dict:
    order = order_repo.get(conn, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order


def cancel_order(conn: sqlite3.Connection, order_id: int) -> dict:
    """Siparişi iptal et ve stoğu geri yükle."""
    order = get_order(conn, order_id)  # 404 kontrolü

    if order["status"] == "cancelled":
        raise HTTPException(status_code=409, detail="order already cancelled")

    # Stoğu geri yükle
    for item in order["items"]:
        product_repo.adjust_stock(conn, item["product_id"], item["quantity"])

    # Statusu güncelle
    return order_repo.update_status(conn, order_id, "cancelled")


def get_revenue_by_category(conn: sqlite3.Connection) -> dict:
    return order_repo.get_revenue_by_category(conn)
