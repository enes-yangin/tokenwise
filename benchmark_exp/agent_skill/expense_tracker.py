"""ExpenseTracker library."""

import csv
import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Expense:
    amount: float
    category: str
    description: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: datetime = field(default_factory=datetime.now)


class ExpenseTracker:
    def __init__(self):
        self._expenses: list[Expense] = []

    def add_expense(self, amount: float, category: str, description: str) -> Expense:
        if amount <= 0:
            raise ValueError("amount must be positive")
        if not category or not category.strip():
            raise ValueError("category must not be empty")
        expense = Expense(amount=amount, category=category, description=description)
        self._expenses.append(expense)
        return expense

    def list_expenses(self, category: str | None = None) -> list[Expense]:
        if category is None:
            return list(self._expenses)
        return [e for e in self._expenses if e.category == category]

    def total_by_category(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for e in self._expenses:
            totals[e.category] = totals.get(e.category, 0.0) + e.amount
        return totals

    def export_csv(self, filepath: str) -> None:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["amount", "category", "description", "date"])
            writer.writeheader()
            for e in self._expenses:
                writer.writerow({
                    "amount": e.amount,
                    "category": e.category,
                    "description": e.description,
                    "date": e.date.isoformat(),
                })
