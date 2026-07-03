# RESULT

## Yaklaşım
FastAPI + stdlib `sqlite3` (ORM yok). Tek dosya `main.py`, `app` export edilir.

- **DB izolasyonu:** `DB_PATH` env değişkeni. Test `:memory:` kullanır; paylaşılan
  in-memory connection (`_memory_conn`) process boyunca yaşar, her test başında
  `None`'a resetlenip taze DB ile başlar. Bağlantı `check_same_thread=False`
  (TestClient handler'ları ayrı thread'de çalıştırır).
- **Atomik stok düşümü:** sipariş oluşturmadan önce tüm ürünler okunur, varlık ve
  stok yeterliliği doğrulanır; herhangi biri başarısızsa hiçbir yazma yapılmaz (409).
- **Fiyat snapshot:** `order_items.unit_price_cents` sipariş anında yazılır;
  `total_cents` her zaman snapshot'tan hesaplanır, ürün PATCH'i geçmişi etkilemez.
- **İptal idempotency:** zaten `cancelled` ise 409, stok geri yüklenmez.
- **Para:** tamamen int (`*_cents`), float yok.
- **Sayfalama:** offset aralık dışıysa boş liste.
- **Referans bütünlüğü:** OrderItem'da referanslı ürün silinemez (409).

## Testler
28 test (`test_api.py`) — tüm endpoint'ler ve SPEC'teki 7 gizli edge case dahil.

## pytest çıktısı
```
28 passed, 59 warnings in 0.66s
```
(warnings: FastAPI `on_event` deprecation — fonksiyonel etkisi yok.)

## Dosyalar
- `main.py` — uygulama
- `test_api.py` — testler
- `requirements.txt`
