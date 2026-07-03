# Feature Görevi: "Orders" kaynağını ekle

Bu kodtabanı katmanlı bir FastAPI uygulaması (`app/` paketi). Mevcut iki kaynak —
**users** ve **products** — net bir 5-katman deseni izliyor:

```
app/models/<x>.py        → SCHEMA (SQL) + to_dict(row)
app/schemas/<x>.py       → pydantic In/Patch
app/repositories/<x>_repo.py → conn alır, veri erişimi
app/services/<x>_service.py   → domain kuralları, HTTPException
app/routers/<x>.py       → FastAPI endpoint'leri
```

Kayıt noktaları:
- `app/db.py` → `_MODEL_MODULES` listesine yeni model modülü eklenir (şema kurulumu)
- `app/main.py` → yeni router import edilip `include_router` ile kaydedilir

## Eklenecek: Orders

Aynı desene uyarak **orders** kaynağını ekle.

### Endpoint Kontratı (BİREBİR)
- `POST /orders`
  - Body: `{"items": [{"product_id": int, "quantity": int}, ...]}`
  - 201 → `{"id", "status": "pending", "created_at", "items": [{"product_id","quantity","unit_price_cents"}], "total_cents"}`
    - `unit_price_cents` sipariş anındaki ürün fiyatından snapshot
    - ilgili ürünlerin `stock`'u düşürülür
  - 409 → herhangi bir kalemde stok yetersiz. **Kısmi düşüm OLMAMALI** (atomik). Aynı ürün birden çok satırda ise toplam miktar kontrol edilir.
  - 404 → product_id yoksa
  - 422 → `quantity <= 0` veya boş items
- `GET /orders/{id}` → 200 (yukarıdaki şekil) | 404
- `POST /orders/{id}/cancel`
  - 200 → status `cancelled`, kalem stokları ürünlere geri yüklenir
  - 404 → sipariş yok
  - 409 → zaten cancelled (idempotency: ikinci iptal stoğu tekrar yüklemez)
- `GET /reports/revenue-by-category`
  - 200 → `{"<category>": <toplam_cents>}` — sadece iptal edilmemiş siparişler, snapshot fiyatlarıyla

### Mevcut katmana dokunan değişiklik (önemli)
- **Referans bütünlüğü:** Bir siparişte (order_items) referanslı ürün **silinemez** →
  `DELETE /products/{id}` artık 409 dönmeli. Bunu products service/repository katmanında ele al.

### Edge case'ler (test edilecek)
1. Atomik stok düşümü (kısmi düşüm yok + aynı ürün çoklu satır toplama)
2. Fiyat snapshot'ı (sonradan PATCH fiyatı değişse geçmiş sipariş total'i değişmez)
3. İptal idempotency (çift iptal → 409, stok iki kat yüklenmez)
4. Para hassasiyeti (int cents, float yok)
5. Referans bütünlüğü (siparişteki ürün silinemez → 409)
6. Validasyon (quantity<=0, boş items → 422)
7. 404'ler (olmayan order / product)

## Teslimat
- Orders için tüm katman dosyaları + kayıtlar
- `tests/test_orders.py` — kendi testlerin
- Mevcut testler (`tests/test_products.py`) hâlâ geçmeli

## Ortam
- Python: `C:/Users/Enes/Desktop/skills/benchmark_deep/.venv/Scripts/python.exe`
- Test: çalışma dizininden `<python> -m pytest -q` (pyproject `pythonpath=["."]` ayarlı, `APP_DB=:memory:` conftest'te)
- fastapi/httpx/pytest KURULU. pip install YAPMA.
