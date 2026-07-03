# RESULT

## Yaklaşım Özeti
- **Tek dosya** `main.py`: FastAPI + stdlib `sqlite3` (ORM yok). Üç tablo: `products`, `orders`, `order_items`.
- **Test izolasyonu**: DB yolu `INVENTORY_DB` env değişkeninden okunur. Testler bunu `:memory:` yapar ve her testte `main.reset_db()` ile tabloları sıfırlar. In-memory bağlantı tek paylaşılan connection üzerinden tutulur (`:memory:` connection-başına yok olduğu için).
- **Para**: tümü `int` cents; float aritmetiği yok. `total_cents` her zaman snapshot fiyatlarından (`order_items.unit_price_cents`) hesaplanır.
- **Validasyon**: Pydantic `Field(ge=0)` / `gt=0` / `min_length=1` ile negatif fiyat/stok/quantity ve boş items → 422.

## Edge case'ler nasıl karşılandı
1. **Atomik stok düşümü**: sipariş oluşturmada önce tüm ürünler ve toplam talep doğrulanır (aynı ürün için tekrarlı kalemler toplanır), yetersizse hiçbir UPDATE yapılmadan 409.
2. **Fiyat snapshot'ı**: fiyat sipariş anında `order_items`'a kopyalanır; sonraki PATCH geçmiş total'i etkilemez.
3. **İptal idempotency**: `status == cancelled` ise ikinci iptal 409; stok ikinci kez geri yüklenmez.
4. **Para hassasiyeti**: tüm hesaplar integer cents.
5. **Sayfalama**: offset liste dışındaysa boş liste (hata değil).
6. **Referans bütünlüğü**: `order_items`'ta referanslı ürün silinemez → 409.
7. **Validasyon**: negatif değerler → 422.

## Testler
- Dosya: `test_api.py`
- **29 test**, hepsi geçiyor. Products (CRUD + filtre/sayfalama + 409 ref), Orders (oluştur/getir/iptal + tüm edge case'ler), Reports (low-stock + revenue-by-category, iptal hariç) kapsanır.

## pytest çıktısı
```
29 passed, 1 warning in ~0.49s
```
(Kalan tek uyarı starlette/httpx kaynaklı `TestClient` deprecation'ı; kendi kodumuzdan değil.)

## Tahmini token kullanımı
**Düşük–orta** — spec okundu, tek geçişte tek modül + tek test dosyası yazıldı, iki kez pytest çalıştırıldı, küçük bir lifespan refaktörü yapıldı.
