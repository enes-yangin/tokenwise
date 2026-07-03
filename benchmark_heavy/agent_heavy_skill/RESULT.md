# RESULT — Orders feature

## Dokunulan dosyalar

### Yeni (orders, 5 katman)
- `app/models/order.py` — `orders` + `order_items` şeması, `to_dict` / `item_to_dict`
- `app/schemas/order.py` — `OrderItemIn` (quantity > 0), `OrderIn` (items min_length=1)
- `app/repositories/order_repo.py` — create / get / get_items / set_status /
  count_active_items_for_product / revenue_by_category
- `app/services/order_service.py` — create_order, get_order, cancel_order,
  revenue_by_category (domain kuralları + HTTPException)
- `app/routers/orders.py` — POST /orders, GET /orders/{id}, POST /orders/{id}/cancel,
  GET /reports/revenue-by-category

### Kayıtlar
- `app/db.py` — `_MODEL_MODULES` listesine `app.models.order` eklendi
- `app/main.py` — orders router import + include_router

### Mevcut katmana değişiklik (referans bütünlüğü)
- `app/services/product_service.py` — `delete_product` artık siparişte referanslı ürün
  için 409 döner (order_repo.count_active_items_for_product kullanır)

### Test
- `tests/test_orders.py` — 12 test (acceptance check, önce yazıldı)

## Testler
- Önce (failing baseline): 9 failed / 3 passed — sebep: orders endpoint'leri yok (404).
- Sonra: **16 passed** (12 orders + 4 mevcut product testi). test_products.py hâlâ yeşil.

Kapsanan edge case'ler: atomik stok düşümü (kısmi düşüm yok), aynı ürün çoklu satır
toplama, fiyat snapshot'ı (sonraki PATCH total'i etkilemez), iptal idempotency (çift
iptal 409, stok iki kat yüklenmez), int cents para hassasiyeti, referans bütünlüğü
(silme 409), validasyon (422), 404'ler, revenue raporu iptal edilmişleri hariç tutar.

## /heavy metrikleri
- Explore subagent: 1 (katman desenini haritaladı; çıktısı yaklaşımı doğruladı,
  beklemeden surgical read ile paralel ilerlendi).
- Debug döngüsü: 0 — implementasyon ilk çalıştırmada tüm testleri geçti.

## Yaklaşım özeti
Mevcut 5-katman desenini birebir mirror'ladım, yeni soyutlama eklemedim. Atomiklik
servis katmanında tek transaction ile sağlandı: tüm stok/404 kontrolleri INSERT/UPDATE
öncesi yapılır, hepsi geçerse uygulanıp tek commit atılır (kısmi düşüm imkânsız). Aynı
ürünün çoklu satırları stok kontrolünde toplanır ama satır bazlı snapshot fiyatla
saklanır. Fiyat snapshot'ı order_items.unit_price_cents'te tutulur, ürün PATCH'i
geçmişi etkilemez. İptal stoğu yalnız status != cancelled iken geri yükler (idempotent).
