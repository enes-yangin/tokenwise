# Görev: Analitik SQL sorguları (SQLite)

Bu dizinde `schema.sql` ve `seed.sql` var. Şemayı oku. Aşağıdaki 4 soruyu yanıtlayan
sorguları **her biri ayrı dosya** olarak yaz: `q1.sql`, `q2.sql`, `q3.sql`, `q4.sql`.
Her dosya TEK bir `SELECT` içerir. SQLite sözdizimi. Kolon adları/sırası ve satır
sırası aşağıda pinlenmiştir — jüri sonucu birebir karşılaştırır.

## q1 — Ödeme yapılmış müşteri gelirleri
En az bir `paid` siparişi olan her müşteri için, SADECE `paid` siparişlerdeki
`qty * unit_price_cents` toplamı.
- Kolonlar: `name`, `revenue_cents`
- Sıra: `revenue_cents` azalan, sonra `name` artan.

## q2 — Ülke başına ödenmiş sipariş sayısı
Her ülke için `paid` durumundaki sipariş sayısı.
- Kolonlar: `country`, `order_count`
- Sıra: `order_count` azalan, sonra `country` artan.

## q3 — Ürün başına satılan adet (ödenmiş)
Her ürün için `paid` siparişlerde satılan toplam `qty`.
- Kolonlar: `product`, `total_qty`
- Sıra: `total_qty` azalan, sonra `product` artan.

## q4 — Hiç ödeme yapmamış müşteriler
Hiç `paid` siparişi OLMAYAN müşterilerin adları.
- Kolon: `name`
- Sıra: `name` artan.

## Doğrulama
Teslim: `q1.sql`..`q4.sql`. Sadece kendi dizininde çalış. İstersen sqlite ile kendin
dene: `python -c "import sqlite3..."` (venv'de sqlite3 stdlib).
