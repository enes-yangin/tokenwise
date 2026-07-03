"""Order iş mantığı — domain kuralları, HTTPException fırlatır."""
import sqlite3

from fastapi import HTTPException

from app.repositories import order_repo, product_repo


def create_order(conn: sqlite3.Connection, items_data: list) -> dict:
    """
    Order oluştur: ürünleri kontrol et, stoğu düşür, order kaydet.
    items_data = [{"product_id": int, "quantity": int}, ...] or [OrderItemIn, ...]
    """
    # Aynı ürün birden çok satırda olabilir → miktarları topla.
    requested: dict[int, int] = {}
    order_lines = []  # girdi sırasını koru (her satır ayrı order_item olur)
    for item_data in items_data:
        # Handle both dict and pydantic model
        if hasattr(item_data, "model_dump"):
            product_id = item_data.product_id
            quantity = item_data.quantity
        else:
            product_id = item_data["product_id"]
            quantity = item_data["quantity"]
        requested[product_id] = requested.get(product_id, 0) + quantity
        order_lines.append((product_id, quantity))

    # Tüm ürünleri kontrol et (stok DEĞİŞTİRMEDEN) — atomiklik için önce doğrula.
    products: dict[int, dict] = {}
    for product_id in requested:
        product = product_repo.get(conn, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail=f"product {product_id} not found")
        products[product_id] = product

    for product_id, total_qty in requested.items():
        if products[product_id]["stock"] < total_qty:
            raise HTTPException(
                status_code=409,
                detail=f"insufficient stock for product {product_id}",
            )

    # Doğrulama geçti → şimdi stoğu düş ve order'ı kaydet.
    order_items = []
    total_cents = 0
    for product_id, quantity in order_lines:
        price = products[product_id]["price_cents"]
        order_items.append(
            {
                "product_id": product_id,
                "quantity": quantity,
                "unit_price_cents": price,
            }
        )
        total_cents += price * quantity

    for product_id, total_qty in requested.items():
        product_repo.adjust_stock(conn, product_id, -total_qty)

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
        raise HTTPException(status_code=409, detail="order already cancelled")

    # Ürün stoğunu geri ver
    for item in order["items"]:
        product_repo.adjust_stock(conn, item["product_id"], item["quantity"])

    # Status'u güncelle
    return order_repo.update_status(conn, order_id, "cancelled")


def get_revenue_by_category(conn: sqlite3.Connection) -> dict:
    """Kategori bazında gelir raporu döndür (pending order'lar için)."""
    return order_repo.get_revenue_by_category(conn)
