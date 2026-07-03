# NET SPEC: "orders" kaynağı (pipe_worker)

Bu, `SPEC_VAGUE.md`'nin belirsizliklerini kaldıran **uygulanabilir** spec'tir. Mevcut
users+products 5-katman desenine (`model / schema / repository / service / router` +
`db.py` & `main.py` kayıtları) BİREBİR uy. Aşağıdaki her kural bağlayıcıdır.

---

## 0. Genel kurallar (gizli kararlar açık)

- **Para birimi:** Tek para birimi, tüm tutarlar **integer cent** (`*_cents`). Currency alanı
  YOK, float YOK, yuvarlama YOK. `total_cents` = satırların `unit_price_cents * quantity`
  toplamı.
- **Fiyat snapshot:** Sipariş oluşturulurken her kalemin `unit_price_cents` değeri o anki
  `products.price_cents`'ten **kopyalanır ve order_items satırına yazılır**. Sonradan ürün
  fiyatı değişse veya ürün silinse bile siparişin `unit_price_cents` ve `total_cents`
  değerleri DEĞİŞMEZ (snapshot). Yanıtlar order_items'tan okunur, canlı products'tan değil.
- **Bağlantı & commit:** repository katmanı `conn` alır; product_repo desenindeki gibi
  yazma işlemlerinden sonra `conn.commit()` çağırır. Servis katmanı `HTTPException` fırlatır.
  Router `Depends(db)` ile `get_conn()` kullanır (products.py ile aynı).
- **Atomiklik:** Sipariş oluşturma tek bir SQLite transaction gibi ele alınır: ya TÜM
  kalemler stoktan düşülüp sipariş yazılır, ya da HİÇBİR değişiklik kalıcı olmaz. Herhangi
  bir kalem hata verirse, o ana kadar yapılmış stok düşümleri geri alınır (aşağıya bak).
- **Zaman:** `created_at` UTC ISO-8601 string (ör. `datetime.now(timezone.utc).isoformat()`),
  DB'de TEXT olarak saklanır ve yanıtta aynen döner.

---

## 1. Veri modeli (`app/models/order.py`)

İki tablo, tek `SCHEMA` string'i içinde (product_model deseni gibi `SCHEMA` ve `to_dict`
expose et). `db.py`'deki `_MODEL_MODULES` listesine `"app.models.order"` EKLE.

```
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL,               -- "active" | "cancelled"
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL,        -- FK YOK; ürün silinse de snapshot korunur (bkz §7)
    quantity INTEGER NOT NULL,
    unit_price_cents INTEGER NOT NULL   -- oluşturma anındaki fiyat snapshot'ı
);
```

- **Status enum:** İki değer: `"active"` (oluşturulmuş, iptal edilmemiş) ve `"cancelled"`.
- `order_items.product_id` üzerinde SQL FK kısıtı KOYMA (ürünün sonradan silinebilmesi
  ve snapshot'ın bozulmaması için). Referans bütünlüğü §7'de tanımlı.

---

## 2. Şemalar (`app/schemas/order.py`)

```
class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)        # quantity >= 1; 0 veya negatif -> 422

class OrderIn(BaseModel):
    items: list[OrderItemIn] = Field(min_length=1)   # boş liste -> 422
```

- Yanıt şemaları için pydantic response model ZORUNLU değil; servis dict döndürmesi yeterli
  (product deseni gibi). İstenirse `OrderItemOut`/`OrderOut` eklenebilir ama şekil §3'e uymalı.

---

## 3. Yanıt şekli (TÜM order döndüren endpoint'ler)

Kesin şekil (alan adları ve sıralaması pinli):

```json
{
  "id": 1,
  "status": "active",
  "created_at": "2026-07-02T12:00:00+00:00",
  "items": [
    {"product_id": 5, "quantity": 2, "unit_price_cents": 500}
  ],
  "total_cents": 1000
}
```

- `items` sırası: order_items.id (yani ekleme sırası) ARTAN.
- `total_cents` her zaman `items` üzerinden hesaplanmış `sum(quantity * unit_price_cents)`.

---

## 4. `POST /orders` — sipariş oluştur

**Girdi:** `{"items": [{"product_id": int, "quantity": int}, ...]}`

**Validasyon (422, pydantic):** `items` boş olamaz; her `quantity >= 1`; `product_id` int.

**İş kuralları (sırayla):**

1. **Aynı ürün birden çok satırda (duplicate product_id):** İstek gövdesindeki satırlar
   `product_id` bazında **birleştirilir (merge/toplanır)**: aynı ürün 2 satırda `qty 1` + `qty 2`
   ise, tek ürün için toplam `qty 3` olarak işlenir. Stok kontrolü ve düşüm toplam miktar
   üzerinden yapılır. Yanıtta o ürün **tek bir kalem** olarak döner (`quantity: 3`).
2. **404 — ürün yok:** Birleştirilmiş product_id'lerden herhangi biri products'ta yoksa
   → **404**, `detail="product not found"`. Hiçbir stok düşürülmez, sipariş yaratılmaz.
3. **Stok yeterlilik kontrolü (all-or-nothing):** TÜM kalemler için `product.stock >= istenen
   toplam qty` ÖNCE topluca kontrol edilir. **Çok kalemli siparişte tek bir kalem bile
   yetersizse, TÜM sipariş reddedilir** → **409**, `detail="insufficient stock"`. Hiçbir
   ürünün stoğu düşmez (kısmi sipariş / kısmi düşüm YASAK). (Öneri: önce hepsini doğrula,
   sonra hepsini düş — atomiklik garantisi.)
4. **Stok düşümü:** Kontroller geçtiyse her ürünün stoğu birleştirilmiş toplam qty kadar
   `adjust_stock(conn, product_id, -qty)` ile düşürülür.
5. **Snapshot & yazım:** `orders` satırı (`status="active"`, `created_at=now`) yazılır; her
   birleştirilmiş kalem için `order_items`'a `unit_price_cents = product.price_cents`
   snapshot'ı ile satır yazılır.

**Başarılı yanıt:** **201**, §3 şekli.

**Hata özeti:**
| Durum | Kod | detail |
|---|---|---|
| items boş / quantity<1 / tip hatası | 422 | (pydantic) |
| product_id bulunamadı | 404 | product not found |
| en az bir kalemde yetersiz stok | 409 | insufficient stock |

---

## 5. `GET /orders/{id}`

- Sipariş varsa **200**, §3 şekli (iptal edilmişse `status="cancelled"`).
- Yoksa **404**, `detail="order not found"`.

---

## 6. `POST /orders/{id}/cancel`

**İş kuralları:**

1. Sipariş yoksa → **404**, `detail="order not found"`.
2. Sipariş `status="active"` ise: statüyü `"cancelled"` yap ve **her kalemin stoğunu geri
   ekle** — her order_item için `adjust_stock(conn, product_id, +quantity)`.
   - **Silinmiş ürün durumu:** İptal sırasında bir order_item'ın `product_id`'si artık
     products'ta yoksa, o kalem için stok iadesi **sessizce atlanır** (hata değil); iptal
     yine de başarılı olur. (order_item snapshot'ı kalıcıdır, canlı ürün olmayabilir.)
3. **İdempotency:** Sipariş zaten `status="cancelled"` ise → **200**, güncel sipariş döner;
   stok TEKRAR geri EKLENMEZ (çift iade YASAK). Yani ikinci ve sonraki cancel çağrıları
   no-op'tur, aynı 200 + aynı body döner. (Hata döndürme; idempotent başarı.)

**Başarılı yanıt:** **200**, güncel sipariş (§3 şekli, `status="cancelled"`).

---

## 7. Referans bütünlüğü — siparişteki ürün silinebilir mi?

- **Evet, silinebilir.** `order_items.product_id` üzerinde DB FK kısıtı yoktur; mevcut
  `DELETE /products/{id}` davranışı DEĞİŞMEZ (orders varlığı ürün silmeyi engellemez).
- Ürün silindikten sonra:
  - İlgili siparişin `GET`/cancel yanıtları order_items snapshot'ından okunur; `product_id`,
    `quantity`, `unit_price_cents`, `total_cents` KORUNUR (canlı products'a bakılmaz).
  - İptalde silinmiş ürünün stok iadesi atlanır (§6.2).
- **Not:** Bu spec, product servisini "sipariş varsa silmeyi engelle" şeklinde DEĞİŞTİRMEZ.
  Snapshot yaklaşımı bu bağımlılığı gereksiz kılar.

---

## 8. `GET /reports/revenue-by-category`

- Dönen şekil: `{"<category>": <toplam_cents>, ...}` (kategori adı → int cents).
- **Gelir tanımı:** Yalnızca `status="active"` siparişlerin kalemleri sayılır; **iptal
  edilmiş siparişler gelire DAHİL EDİLMEZ**.
- **Kategori kaynağı:** Kalemin kategorisi, o kalemin `product_id`'sine karşılık gelen canlı
  `products.category`'sinden alınır (JOIN). Kalem başına gelir = `quantity * unit_price_cents`
  (snapshot fiyatı; canlı fiyat değil).
- **Silinmiş ürün:** Kalemin ürünü silinmişse kategori bulunamaz; bu kalem rapordan **hariç
  tutulur** (kategori-less geliri toplama). (Basit ve deterministik davranış.)
- Hiç gelir yoksa boş dict `{}` döner.
- Router path'i: **`GET /reports/revenue-by-category`** (prefix'siz, `/orders` altında DEĞİL).
  Ayrı bir router (`app/routers/reports.py`) veya orders router'ına eklenebilir; path tam
  olarak yukarıdaki gibi olmalı. `main.py`'de include et.

---

## 9. Katman yerleşimi (oluşturulacak dosyalar)

- `app/models/order.py` — `SCHEMA` (2 tablo) + `to_dict` yardımcıları.
- `app/schemas/order.py` — `OrderItemIn`, `OrderIn`.
- `app/repositories/order_repo.py` — CRUD + kalem yazma/okuma; `product_repo.adjust_stock`
  ve `product_repo.get` yeniden kullanılır (stok düşüm/iade, fiyat snapshot için).
- `app/services/order_service.py` — §4/§6/§8 domain kuralları; `HTTPException` fırlatır.
- `app/routers/orders.py` — `POST /orders`, `GET /orders/{id}`, `POST /orders/{id}/cancel`.
- `app/routers/reports.py` (veya orders router'ında) — `GET /reports/revenue-by-category`.
- **`app/db.py`:** `_MODEL_MODULES`'e `"app.models.order"` ekle.
- **`app/main.py`:** yeni router(lar)ı import et + `app.include_router(...)`.

---

## 10. Testler (`tests/test_orders.py`)

Aşağıdaki senaryoları KAPSA (conftest `client` fixture'ını kullan; her test temiz :memory:).
Her testte önce ürünleri `POST /products` ile oluştur.

1. **Mutlu yol:** ürün oluştur (stock=10, price=500), `POST /orders` qty=2 → 201; yanıt
   `total_cents==1000`, `status=="active"`, items şekli doğru; ardından ürün stoğu 8'e düşmüş.
2. **404 ürün yok:** olmayan product_id ile sipariş → 404.
3. **409 yetersiz stok (tek kalem):** stock=1, qty=5 → 409; ürün stoğu değişmemiş (hâlâ 1).
4. **409 çok kalemli, tek kalem yetersiz → tümü reddedilir:** A(stock=10) + B(stock=0)
   siparişi → 409; A'nın stoğu düşmemiş (all-or-nothing kanıtı).
5. **Aynı ürün iki satırda birleşir:** aynı product_id iki kez (qty 1 ve 2) → 201; yanıtta
   TEK kalem qty=3, stok 3 düşmüş.
6. **Fiyat snapshot:** sipariş sonrası ürün fiyatını `PATCH` ile değiştir → `GET /orders/{id}`
   hâlâ eski `unit_price_cents`/`total_cents` döner.
7. **İptal + stok iadesi:** sipariş → cancel → 200, status="cancelled"; ürün stoğu iade edilmiş.
8. **İptal idempotency:** aynı siparişi iki kez cancel → ikisi de 200; stok yalnızca BİR kez
   iade edilmiş (çift iade yok).
9. **422 validasyon:** boş `items` ve `quantity=0` → 422.
10. **Revenue raporu:** iki kategoride active siparişler + bir iptal edilmiş sipariş →
    rapor yalnızca active gelirleri kategori bazında toplar; iptal edilen dahil değil.
11. **Silinmiş ürün / snapshot:** sipariş ver, ürünü sil, `GET /orders/{id}` snapshot'ı
    korur (200, doğru total).

**Regresyon:** `tests/test_products.py` değişmeden geçmeli. `pip install` YOK.
Test komutu: çalışma dizininden `<python> -m pytest -q`.

---

## 11. Kabul kriterleri (checklist)

- [ ] 5-katman deseni birebir; `db.py` + `main.py` kayıtları yapıldı.
- [ ] Para tamamen integer cents; float yok.
- [ ] Fiyat order_items'a snapshot'lanıyor; sonraki fiyat/silme değişimlerinden etkilenmiyor.
- [ ] Oluşturma all-or-nothing: tek kalem yetersizse hiçbir stok düşmüyor (409).
- [ ] Aynı ürün iki satırda birleşiyor (tek kalem, toplam qty).
- [ ] Cancel stok iade ediyor; idempotent (çift iade yok); zaten iptal → 200 no-op.
- [ ] 404 (order/product not found), 409 (insufficient stock), 422 (validasyon) doğru.
- [ ] Rapor yalnızca active siparişleri, snapshot fiyatı ve canlı kategoriyle topluyor.
- [ ] Silinmiş ürün siparişi bozmuyor; rapordan hariç; iptalde iadesi atlanıyor.
- [ ] test_orders.py yukarıdaki 11 senaryoyu kapsıyor; test_products.py hâlâ geçiyor.
