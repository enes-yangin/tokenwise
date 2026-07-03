# Feature Görevi: "Orders" kaynağını ekle

Bu katmanlı FastAPI kodtabanına (app/ paketi, mevcut users + products kaynakları aynı
5-katman deseninde) bir **orders** (sipariş) kaynağı ekle. Mevcut desene uy.

Bir sipariş, ürünlerden satın alma yapar. Müşteri birkaç ürün seçer, sipariş oluşturulur,
istenirse iptal edilebilir. Yöneticiler kategori bazında gelir raporu ister.

## Endpoint'ler (yanıt şekilleri pinli)

- `POST /orders` — gövde: `{"items": [{"product_id": int, "quantity": int}, ...]}`
  - Başarılı: 201, yanıt: `{"id", "status", "created_at", "items": [{"product_id","quantity","unit_price_cents"}], "total_cents"}`
  - Sipariş verilince ilgili ürünlerin stoğu düşer.
- `GET /orders/{id}` — 200 (yukarıdaki şekil) | bulunamazsa uygun hata
- `POST /orders/{id}/cancel` — siparişi iptal eder; iptal edilen siparişin ürünleri stoğa geri döner. Yanıt: güncel sipariş.
- `GET /reports/revenue-by-category` — `{"<category>": <toplam_cents>}` döndürür.

## Beklentiler
- Mevcut katman desenine uy (model/schema/repository/service/router + db.py & main.py kayıtları).
- Hataları makul şekilde ele al.
- `tests/test_orders.py` ile kendi testlerini yaz.
- Mevcut testler (test_products.py) hâlâ geçmeli.

## Ortam
- Python: `C:/Users/Enes/Desktop/skills/benchmark_deep/.venv/Scripts/python.exe`
- Test: çalışma dizininden `<python> -m pytest -q` (pythonpath ve :memory: ayarlı)
- fastapi/httpx/pytest KURULU. pip install YAPMA.
