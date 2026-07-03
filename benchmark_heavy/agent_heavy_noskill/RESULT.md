# RESULT — Orders kaynağı

## Dokunulan dosyalar

### Yeni (orders katmanı)
- `app/models/order.py` — orders + order_items şeması, `to_dict(order_row, item_rows)` (total_cents hesaplar)
- `app/schemas/order.py` — `OrderIn` (items min_length=1), `OrderItemIn` (quantity gt=0)
- `app/repositories/order_repo.py` — create/get/set_status/count_items_for_product/revenue_by_category
- `app/services/order_service.py` — domain kuralları + HTTPException
- `app/routers/orders.py` — POST /orders, GET /orders/{id}, POST /orders/{id}/cancel, GET /reports/revenue-by-category
- `tests/test_orders.py` — 10 test

### Değiştirilen (kayıtlar + referans bütünlüğü)
- `app/db.py` — `_MODEL_MODULES`'a `app.models.order` eklendi
- `app/main.py` — orders router import + include_router
- `app/services/product_service.py` — `delete_product` artık siparişte referanslı ürün için 409 döner (order_repo.count_items_for_product)

## Testler
`<python> -m pytest -q` → **14 passed** (4 mevcut products + 10 yeni orders). Mevcut test_products.py bozulmadan geçiyor.

Kapsanan edge case'ler: atomik stok düşümü (kısmi yok), aynı ürün çoklu satır toplama, fiyat snapshot (sonraki PATCH'ten etkilenmez), iptal idempotency (çift iptal 409, stok iki kat yüklenmez), int cents para hassasiyeti, referans bütünlüğü (409), validasyon (422), 404'ler, revenue raporu iptalleri hariç tutuyor.

## Yaklaşım
Mevcut 5 katmanlı users/products desenine birebir uyuldu. Stok atomikliği servis katmanında "önce tüm kontroller, sonra tüm yazımlar" sırasıyla sağlandı; aynı product_id'li satırlar stok kontrolü için toplanır ama snapshot kalemleri ayrı satır olarak saklanır. Fiyat, sipariş anında order_items.unit_price_cents'e kopyalanarak snapshot edilir. Rapor, iptal edilmemiş siparişlerin order_items × products JOIN'i ile kategori bazında toplanır.
