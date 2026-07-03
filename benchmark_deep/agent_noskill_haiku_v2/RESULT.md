# FastAPI REST API - Envanter & Sipariş Yönetim Sistemi

## Yaklaşım Özeti

Spec'te tanımlanan REST API'yi FastAPI + SQLite ile uyguladım. Aşağıdaki temel kararlar alındı:

### Mimari
- **Database**: SQLite3 stdlib (ORM yok, basit ve doğrudan)
- **Validation**: Pydantic v2 modelleri tüm inputs için
- **Transaction Yönetimi**: Atomik stok güncellemeleri sağlamak için manuel transaction control
- **Test Isolation**: Her test için bağımsız temp database, veritabanı durumu izole kalıyor

### Kritik Özellikler

1. **Atomik Stok Düşümü**: Çok kalemli siparişte hata durumunda hiçbir ürünün stoğu değişmiyor. Tüm ürünlerin stoğu kontrolü yapıldıktan sonra, hepsi başarısız olursa transaksiyon geri alınır.

2. **Fiyat Snapshot'ı**: Her order item, sipariş anındaki ürün fiyatını (`unit_price_cents`) kaydeder. Sonradan ürün fiyatı güncellense de, geçmiş siparişin toplam tutarı değişmez.

3. **İptal İdempotency**: Siparişin status'u kontrol edilerek, zaten iptal edilen sipariş tekrar iptal edilirse 409 dönülür. Stok iki kat geri yüklenmez.

4. **Referans Bütünlüğü**: Herhangi bir order item'de referans edilen ürün silinemez (409).

5. **Validasyon**: 
   - Negatif fiyat/stok/quantity → 422
   - Boş items listesi → 422
   - Quantity <= 0 → 422

6. **Sayfalama**: Offset listenin dışındaysa boş liste döner, hata değil.

### Dosyalar

- **main.py** (341 satır): FastAPI uygulaması, tüm endpoints
  - 7 Product endpoints (CRUD + filtre + sayfalama)
  - 5 Order endpoints (CRUD + cancel)
  - 2 Report endpoints
  
- **test_main.py** (450+ satır): Kapsamlı pytest test paketi
  - 34 test case (tüm edge case'leri kapsıyor)
  - Başlıca kategoriler:
    - Product creation, filtering, update, delete (9 test)
    - Order creation, stock atomicity, cancellation (10 test)
    - Reports & price snapshots (6 test)

## Test Sonuçları

```
34 passed in 1.79s
```

### Test Kapsamı

- ✓ Ürün CRUD operasyonları
- ✓ SKU uniqueness constraint
- ✓ Sayfalama ve filtreleme
- ✓ Sipariş oluşturma (single & multi-item)
- ✓ Atomik stok düşümü (fail-safe)
- ✓ Stok yetersizliği testi
- ✓ Sipariş iptali ve stok geri yüklemesi
- ✓ İptal idempotency
- ✓ Fiyat snapshot'ı (sipariş sonrası fiyat değişse de eski fiyat korunur)
- ✓ Revenue report (sadece cancelled olmayan orders)
- ✓ Low stock report (threshold filtreleme)
- ✓ Validation hataları (negatif değerler, boş listeler, vb.)
- ✓ Referansa dayalı silme kısıtlaması

## İmplementasyon Detayları

### Database Schema

```sql
products:
  id (int, autoincrement)
  name (str)
  sku (str, UNIQUE)
  price_cents (int)
  stock (int)
  category (str)

orders:
  id (int, autoincrement)
  status (str: pending|paid|cancelled)
  created_at (ISO str)

order_items:
  id (int, autoincrement)
  order_id (FK)
  product_id (FK)
  quantity (int)
  unit_price_cents (int) - snapshot
```

### Test Stratejisi

- **Fixture**: Her test için `tempfile` ile yeni bir SQLite database
- **Database reload**: `importlib.reload(main)` kullanarak her test yeni DB path'ı alır
- **Cleanup**: Test sonrası temp file otomatik silinir

## Gizli Edge Case'ler ve Çözümleri

| Edge Case | Çözüm |
|-----------|-------|
| Çok kalemli siparişte kısmi fail | Pre-check tüm ürünleri → tümü başarısız olursa 409, stok değişmez |
| Fiyat değişimi sonrası sipariş | Snapshot: `unit_price_cents` siparış anındaki fiyatı tutar |
| Çift iptal | Status check → 409, stok iki kat geri yüklenmez |
| Offset out of range | Boş liste return, hata değil |
| Ürün siparişle bağlıyken silme | FK check → 409 |
| Validasyon hataları | Pydantic validators + HTTP 422 |

## Kurtarma Noktaları

Test başarısızlığı durumunda kontrol edilmesi gereken:
1. Database isolation: her test kendi temp DB'yi alıyor
2. Stock atomicity: create_order fonksiyonu pre-check → update flow
3. Price snapshots: unit_price_cents kaydediliyor vs product price değişebiliyor
