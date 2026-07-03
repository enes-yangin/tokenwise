# Görev: Envanter & Sipariş Yönetim REST API'si

FastAPI + SQLite ile bir REST API yaz. API kontratı aşağıda **kesin** olarak
pinlenmiştir — yolları, JSON şekillerini ve status kodlarını birebir uygula.

## Zorunlu Giriş Noktası
- `main.py` içinde `app` adında bir FastAPI nesnesi export et.
- Bağımsız bir test paketi `from main import app` ile `TestClient(app)` kuracak.
- Veritabanı varsayılan olarak dosya tabanlı SQLite, ama test edilebilir olmalı
  (her TestClient örneği temiz bir DB ile başlayabilmeli — örn. env değişkeni veya
  `:memory:` desteği). **Önemli:** testler izole çalışmalı.

## Varlıklar (SQLite, kalıcı)
- **Product**: `id` (int, auto), `name` (str), `sku` (str, UNIQUE), `price_cents` (int), `stock` (int), `category` (str)
- **Order**: `id` (int, auto), `status` (`pending`|`paid`|`cancelled`), `created_at` (ISO str)
- **OrderItem**: `order_id`, `product_id`, `quantity`, `unit_price_cents` (sipariş anındaki fiyat snapshot'ı)

## Endpoint Kontratı

### Products
- `POST /products`
  - Body: `{"name": str, "sku": str, "price_cents": int, "stock": int, "category": str}`
  - 201 → oluşturulan ürün (id dahil)
  - 409 → sku zaten varsa
  - 422 → `price_cents < 0` veya `stock < 0` veya eksik alan
- `GET /products?category=<str>&limit=<int>&offset=<int>`
  - 200 → ürün listesi. `category` verilirse filtrele. `limit` (varsayılan 50), `offset` (varsayılan 0) ile sayfalama.
- `GET /products/{id}` → 200 | 404
- `PATCH /products/{id}`
  - Body: kısmi alanlar (örn. `{"price_cents": 200}`)
  - 200 → güncel ürün | 404
- `DELETE /products/{id}`
  - 204 → silindi
  - 404 → yoksa
  - 409 → ürün herhangi bir siparişte (OrderItem) referanslıysa silinemez

### Orders
- `POST /orders`
  - Body: `{"items": [{"product_id": int, "quantity": int}, ...]}`
  - 201 → oluşturulan sipariş: `{"id", "status": "pending", "created_at", "items": [...], "total_cents": int}`
    - her item için `unit_price_cents` o anki ürün fiyatından snapshot alınır
    - sipariş oluşunca ilgili ürünlerin `stock`'u düşürülür
  - 409 → herhangi bir kalemde stok yetersizse. **Kısmi düşüm OLMAMALI** — hiçbir ürünün stoğu değişmez.
  - 404 → product_id yoksa
  - 422 → `quantity <= 0` veya boş items
- `GET /orders/{id}`
  - 200 → sipariş + kalemler + `total_cents` (snapshot fiyatlarından hesaplanır)
  - 404
- `POST /orders/{id}/cancel`
  - 200 → status `cancelled` olur, kalemlerdeki stok ürünlere geri yüklenir
  - 404 → sipariş yoksa
  - 409 → sipariş zaten `cancelled` ise (idempotency: ikinci iptal stoğu tekrar yüklememeli)

### Reports
- `GET /reports/low-stock?threshold=<int>`
  - 200 → `stock <= threshold` olan ürünler (varsayılan threshold=10)
- `GET /reports/revenue-by-category`
  - 200 → `{"<category>": <toplam_cents>, ...}` — sadece **iptal edilmemiş** siparişlerin kalemlerinden, snapshot fiyatlarıyla hesaplanır

## Gizli Edge Case'ler (DİKKAT — bunlar test edilecek)
1. **Atomik stok düşümü:** çok kalemli siparişte bir kalem yetersizse → 409 ve hiçbir stok değişmez.
2. **Fiyat snapshot'ı:** sipariş sonrası ürün fiyatı PATCH ile değişse bile, geçmiş siparişin `total_cents`'i değişmez.
3. **İptal idempotency:** iki kez iptal → ikinci çağrı 409, stok iki kat geri yüklenmez.
4. **Para hassasiyeti:** tüm para `price_cents` (int). Float aritmetiği kullanma.
5. **Sayfalama sınırları:** offset listenin dışındaysa boş liste, hata değil.
6. **Referans bütünlüğü:** siparişte geçen ürün silinemez (409).
7. **Validasyon:** negatif fiyat/stok/quantity → 422.

## Teslimat
- `main.py` (ve istersen ek modüller: db, models, services)
- `test_*.py` — kendi pytest testlerin (en az %80 kapsam hedefle)
- `pyproject.toml` veya `requirements.txt`
- `RESULT.md`: kaç test yazdın, pytest çıktısı, yaklaşımının özeti

## Kısıtlamalar
- FastAPI + stdlib `sqlite3` (ORM kullanmak istersen serbest ama gerekmiyor).
- Test için FastAPI `TestClient` kullan.
- Çalışma dizininden DIŞARI çıkma.
