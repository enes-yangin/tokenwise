# RESULT

## Yaklaşım (/heavy disiplini uygulandı)

1. **Acceptance check önce:** Implementasyondan ÖNCE `test_api.py` yazıldı; SPEC'teki
   7 gizli edge case'in her biri için açık bir test kondu. Testler önce `main` yokken
   çalıştırılıp doğru sebepten (ModuleNotFoundError) başarısız olduğu doğrulandı,
   sonra minimum kod ile geçirildi.
2. **External memory:** `NOTES.md` — kararlar, dosya haritası, izolasyon stratejisi.
3. **Cache bozma yok:** SPEC bir kez okundu, dosyalar tekrar tekrar re-read edilmedi.

## Mimari
- Tek `main.py`: FastAPI + stdlib `sqlite3` (ORM yok). `app` export edilir.
- Para tamamen `int` (`price_cents`) — float aritmetiği yok.
- **Test izolasyonu:** `conftest.py` her testte `DB_PATH=:memory:` set edip
  `importlib.reload(main)` ile taze in-memory DB kurar. Testler birbirinden bağımsız.

## Kilit edge case çözümleri
- **Atomik stok:** siparişte önce TÜM kalemler doğrulanır (varlık + stok), ancak
  hepsi geçerse tek transaction'da stok düşürülür → kısmi düşüm yok (409).
- **Fiyat snapshot:** `order_items.unit_price_cents` sipariş anında yazılır;
  `total_cents` her zaman snapshot'tan hesaplanır → sonradan PATCH etkisiz.
- **İptal idempotency:** zaten `cancelled` ise 409; restock yalnız geçişte yapılır.
- **Referans bütünlüğü:** OrderItem'da referanslı ürün silinemez (409).
- **Validasyon:** pydantic `conint(ge=0)` / `conint(gt=0)` + `min_length=1` → 422.
- **Sayfalama:** offset liste dışıysa boş liste, hata değil.

## Test sonucu
- 22 test yazıldı, tümü geçti.

```
$ ../../benchmark_deep/.venv/Scripts/python.exe -m pytest -q
......................                                            [100%]
22 passed, 1 warning in 0.33s
```

(Uyarı: starlette TestClient'ın httpx deprecation notu — kod değil, kütüphane kaynaklı.)

## Teslim edilen dosyalar
- `main.py`, `conftest.py`, `test_api.py`, `requirements.txt`, `NOTES.md`, `RESULT.md`
