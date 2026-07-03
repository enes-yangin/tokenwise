# RESULT

## Test sayısı
**23 test** (`test_main.py`), spec'teki **7 gizli edge case'in her biri için ayrı test** dahil.

## Pytest çıktısı
```
collected 23 items
test_main.py ....................... [100%]
======================== 23 passed, 1 warning in ~1.1s ========================
coverage: main.py  164 stmts, 12 miss, 93%
```
- **Geçen: 23 / Kalan: 0**
- Kapsam **%93** (hedef %80 aşıldı).
- Kalan tek uyarı: starlette/httpx TestClient deprecation — bağımlılık kaynaklı, kod ile ilgisi yok.

## Yaklaşım özeti
- **Tek dosya** `main.py`: FastAPI + stdlib `sqlite3` (ORM yok, spekülatif soyutlama yok).
- **DB izolasyonu:** `DATABASE_URL` env değişkeni. `:memory:` verildiğinde tek bir paylaşılan
  bağlantı tutulur (her yeni `:memory:` bağlantısı boş DB açacağı için zorunlu).
  Test paketi import'tan önce `DATABASE_URL=:memory:` set eder; `lifespan` her TestClient
  context'inde `init_db()` çağırıp şemayı sıfırdan kurar → her test temiz DB.
- **Atomiklik:** siparişte önce tüm ürünler çözülür ve stok yeterliliği (aynı ürünün
  tekrarlı kalemleri toplanarak) kontrol edilir; tek bir kalem bile yetersizse hiçbir
  INSERT/UPDATE yapılmadan 409 döner → kısmi düşüm yok.
- **Fiyat snapshot:** `order_items.unit_price_cents` sipariş anında yazılır; `total_cents`
  her zaman snapshot'tan hesaplanır, ürün PATCH'i geçmişi etkilemez.
- **İptal idempotency:** `status == cancelled` ise 409, restock yapılmaz.
- **Para:** tüm tutarlar `int` cent; float aritmetiği yok.
- **Validasyon:** pydantic `conint(ge=0)` / `conint(gt=0)` / `min_length` → eksik/negatif
  alanlar otomatik 422.
- **Referans bütünlüğü:** `order_items`'ta referanslı ürün silinmeye çalışılırsa 409.

## İterasyon / debug döngüsü
- **0 debug döngüsü.** Testler ilk çalıştırmada 23/23 geçti (tek seferde yeşil).
- Sonradan yalnızca **kozmetik iyileştirme**: `on_event("startup")` → `lifespan` handler'a
  geçiş (deprecation uyarısını kaldırmak için) ve fixture'daki gereksiz `init_db()` çağrısının
  silinmesi. Davranış değişmedi, testler hâlâ yeşil.

## Tahmini token kullanımı
**Düşük–orta.** SPEC tek seferde okundu, dosyalar cerrahi yazıldı/düzenlendi, dosyalar
tekrar tekrar okunmadı, hiçbir başarısız-test/tahmin döngüsüne girilmedi.
