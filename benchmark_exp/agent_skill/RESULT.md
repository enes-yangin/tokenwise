# ExpenseTracker — TDD Result

## Test Count
29 tests across 5 test classes:
- `TestExpenseDataclass` (5 tests)
- `TestAddExpense` (8 tests)
- `TestListExpenses` (6 tests)
- `TestTotalByCategory` (5 tests)
- `TestExportCSV` (5 tests)

## Pytest Output
```
============================= 29 passed in 0.24s ==============================
```
All 29 tests pass. Zero failures, zero errors.

## Approach Summary

**Iterasyonlar: 1 (tek geçiş)**

1. **Red phase** — `test_expense_tracker.py` tamamen yazıldı. Her metod için edge case'ler dahil testler tanımlandı (amount <= 0, boş/whitespace category, bilinmeyen category filtresi, float precision, boş tracker CSV export'u vb.).
2. **Green phase** — `expense_tracker.py` yazıldı. İlk implementasyon tüm testleri geçti; yeniden düzenleme gerekmedi.
3. **Refactor phase** — Kod zaten minimal ve temiz; ek refactor gerekmedi.

`pyproject.toml` da oluşturuldu (pytest config ve proje metadata içeriyor).

## Tahmini Token Kullanımı
**Düşük** — Tek iterasyonda tüm testler geçti. Dosyalar küçük ve odaklı. Gereksiz araştırma veya tekrar gerekmedi.
