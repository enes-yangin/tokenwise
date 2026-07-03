# Görev: TTL destekli LRU Cache (saf Python)

`lru.py` dosyasında `LRUCache` sınıfını yaz. Harici bağımlılık YOK (sadece stdlib).

## Arayüz (birebir)

```python
class LRUCache:
    def __init__(self, capacity: int, ttl: float, now=None): ...
    def put(self, key, value) -> None: ...
    def get(self, key):   # değeri döndürür; yoksa VEYA süresi dolmuşsa None
    def __len__(self) -> int:   # süresi dolmamış öğe sayısı
```

- `now`: argümansız, geçerli zamanı saniye (float) olarak döndüren bir callable.
  `None` verilirse `time.monotonic` kullan. Tüm zaman damgaları `now()` ile alınır
  (test edilebilirlik için — jüri sahte bir saat enjekte edecek).
- `ttl`: bir öğenin saniye cinsinden yaşam süresi. Yazıldığı andan `ttl` saniye
  SONRA (yani `now() - yazılma_zamanı >= ttl`) öğe **süresi dolmuş** sayılır.

## Kurallar (gizli test edilecek edge case'ler)

1. **Temel**: `put` sonra `get` değeri döndürür.
2. **Miss**: olmayan anahtar → `None`.
3. **LRU tahliye**: kapasite aşılınca **en az yakın zamanda kullanılan** öğe atılır.
   Hem `get` hem `put` bir öğeyi "kullanılmış" (en yeni) yapar.
4. **get koruması**: bir öğeyi `get` ile okumak onu tahliyeden korur (MRU yapar).
5. **Var olan anahtarı güncelleme**: aynı anahtara tekrar `put` → değeri değiştirir,
   öğeyi MRU yapar, yeni öğe SAYILMAZ (kapasiteyi şişirmez).
6. **TTL dolması**: `ttl` geçtikten sonra `get` → `None` (ve öğe kaldırılır).
7. **TTL içinde**: `ttl` dolmadan `get` → değeri döndürür.
8. **`__len__`**: süresi dolmuş öğeleri saymaz.
9. **capacity 0**: hiçbir şey saklanmaz; her `get` → `None`, `len` → 0.
10. **Süresi dolmuş öğe tahliye sayılmaz**: dolu cache'te süresi geçmiş bir öğe
    varsa, yeni `put` önce süresi geçeni temizleyip yer açabilir.

## Doğrulama
`lru.py` importlanabilir olmalı. Kendi hızlı testini yazabilirsin ama teslim edilen
tek dosya `lru.py`. Sadece kendi dizininde çalış.
