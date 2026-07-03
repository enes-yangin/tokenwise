# Görev: Python Gider Takip Kütüphanesi

Aşağıdaki özelliklere sahip bir Python kütüphanesi yaz:

## Gereksinimler

### `ExpenseTracker` sınıfı
- `add_expense(amount: float, category: str, description: str) -> Expense`
  - amount sıfır veya negatif ise ValueError fırlat
  - category boş string ise ValueError fırlat
- `list_expenses(category: str | None = None) -> list[Expense]`
  - category verilirse sadece o kategorideki giderleri döndür
- `total_by_category() -> dict[str, float]`
  - Her kategorinin toplam tutarını döndür
- `export_csv(filepath: str) -> None`
  - Tüm giderleri CSV dosyasına yaz (amount, category, description, date sütunları)

### `Expense` dataclass
- id (uuid)
- amount (float)
- category (str)
- description (str)
- date (datetime, default=now)

## Beklenenler
- Testler (pytest ile, en az %80 kapsam)
- requirements.txt veya pyproject.toml
- Temiz, okunabilir kod

## Kısıtlamalar
- Sadece Python stdlib + pytest kullan (harici bağımlılık yok)
- Veritabanı yok, sadece in-memory
