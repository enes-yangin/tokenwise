from __future__ import annotations

import csv
import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Expense:
    id: str
    amount: float
    category: str
    description: str
    date: datetime = field(default_factory=datetime.now)


class ExpenseTracker:
    def __init__(self) -> None:
        self._expenses: list[Expense] = []

    def add_expense(self, amount: float, category: str, description: str) -> Expense:
        if amount <= 0:
            raise ValueError("amount must be greater than 0")
        if not category:
            raise ValueError("category must not be empty")
        expense = Expense(
            id=str(uuid.uuid4()),
            amount=amount,
            category=category,
            description=description,
        )
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
