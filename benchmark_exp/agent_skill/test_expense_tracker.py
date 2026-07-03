"""Tests for ExpenseTracker - written before implementation (TDD)."""

import csv
import os
import pytest
from datetime import datetime
from unittest.mock import patch

from expense_tracker import Expense, ExpenseTracker


# ── Expense dataclass ──────────────────────────────────────────────────────────

class TestExpenseDataclass:
    def test_expense_has_required_fields(self):
        e = Expense(amount=10.0, category="food", description="lunch")
        assert e.amount == 10.0
        assert e.category == "food"
        assert e.description == "lunch"

    def test_expense_id_is_uuid_string(self):
        e = Expense(amount=5.0, category="transport", description="bus")
        import uuid
        uuid.UUID(e.id)  # raises if not valid UUID

    def test_expense_ids_are_unique(self):
        e1 = Expense(amount=1.0, category="a", description="x")
        e2 = Expense(amount=2.0, category="b", description="y")
        assert e1.id != e2.id

    def test_expense_date_defaults_to_now(self):
        before = datetime.now()
        e = Expense(amount=1.0, category="a", description="x")
        after = datetime.now()
        assert before <= e.date <= after

    def test_expense_date_can_be_set_explicitly(self):
        d = datetime(2024, 1, 15, 10, 30)
        e = Expense(amount=1.0, category="a", description="x", date=d)
        assert e.date == d


# ── add_expense ────────────────────────────────────────────────────────────────

class TestAddExpense:
    def setup_method(self):
        self.tracker = ExpenseTracker()

    def test_add_expense_returns_expense(self):
        result = self.tracker.add_expense(50.0, "food", "pizza")
        assert isinstance(result, Expense)

    def test_add_expense_stores_correctly(self):
        e = self.tracker.add_expense(50.0, "food", "pizza")
        assert e.amount == 50.0
        assert e.category == "food"
        assert e.description == "pizza"

    def test_add_expense_zero_raises(self):
        with pytest.raises(ValueError):
            self.tracker.add_expense(0, "food", "pizza")

    def test_add_expense_negative_raises(self):
        with pytest.raises(ValueError):
            self.tracker.add_expense(-10.0, "food", "pizza")

    def test_add_expense_empty_category_raises(self):
        with pytest.raises(ValueError):
            self.tracker.add_expense(10.0, "", "pizza")

    def test_add_expense_whitespace_category_raises(self):
        with pytest.raises(ValueError):
            self.tracker.add_expense(10.0, "   ", "pizza")

    def test_add_multiple_expenses(self):
        self.tracker.add_expense(10.0, "food", "a")
        self.tracker.add_expense(20.0, "food", "b")
        assert len(self.tracker.list_expenses()) == 2

    def test_add_expense_empty_description_allowed(self):
        e = self.tracker.add_expense(10.0, "food", "")
        assert e.description == ""


# ── list_expenses ──────────────────────────────────────────────────────────────

class TestListExpenses:
    def setup_method(self):
        self.tracker = ExpenseTracker()
        self.tracker.add_expense(10.0, "food", "a")
        self.tracker.add_expense(20.0, "transport", "b")
        self.tracker.add_expense(30.0, "food", "c")

    def test_list_all_expenses_no_filter(self):
        result = self.tracker.list_expenses()
        assert len(result) == 3

    def test_list_expenses_by_category(self):
        result = self.tracker.list_expenses(category="food")
        assert len(result) == 2
        assert all(e.category == "food" for e in result)

    def test_list_expenses_unknown_category_returns_empty(self):
        result = self.tracker.list_expenses(category="health")
        assert result == []

    def test_list_expenses_returns_list_type(self):
        assert isinstance(self.tracker.list_expenses(), list)

    def test_list_expenses_empty_tracker(self):
        t = ExpenseTracker()
        assert t.list_expenses() == []

    def test_list_expenses_none_category_returns_all(self):
        result = self.tracker.list_expenses(category=None)
        assert len(result) == 3


# ── total_by_category ─────────────────────────────────────────────────────────

class TestTotalByCategory:
    def setup_method(self):
        self.tracker = ExpenseTracker()

    def test_empty_tracker_returns_empty_dict(self):
        assert self.tracker.total_by_category() == {}

    def test_single_category_total(self):
        self.tracker.add_expense(10.0, "food", "a")
        self.tracker.add_expense(20.0, "food", "b")
        result = self.tracker.total_by_category()
        assert result == {"food": 30.0}

    def test_multiple_categories(self):
        self.tracker.add_expense(10.0, "food", "a")
        self.tracker.add_expense(20.0, "transport", "b")
        self.tracker.add_expense(5.0, "food", "c")
        result = self.tracker.total_by_category()
        assert result["food"] == pytest.approx(15.0)
        assert result["transport"] == pytest.approx(20.0)

    def test_returns_dict_type(self):
        assert isinstance(self.tracker.total_by_category(), dict)

    def test_float_precision(self):
        self.tracker.add_expense(0.1, "misc", "a")
        self.tracker.add_expense(0.2, "misc", "b")
        result = self.tracker.total_by_category()
        assert result["misc"] == pytest.approx(0.3)


# ── export_csv ────────────────────────────────────────────────────────────────

class TestExportCSV:
    def setup_method(self):
        self.tracker = ExpenseTracker()
        self.filepath = "C:/Users/Enes/AppData/Local/Temp/claude/test_expenses.csv"

    def teardown_method(self):
        if os.path.exists(self.filepath):
            os.remove(self.filepath)

    def test_export_creates_file(self):
        self.tracker.add_expense(10.0, "food", "pizza")
        self.tracker.export_csv(self.filepath)
        assert os.path.exists(self.filepath)

    def test_export_csv_has_header(self):
        self.tracker.add_expense(10.0, "food", "pizza")
        self.tracker.export_csv(self.filepath)
        with open(self.filepath, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert "amount" in header
        assert "category" in header
        assert "description" in header
        assert "date" in header

    def test_export_csv_contains_data(self):
        self.tracker.add_expense(10.0, "food", "pizza")
        self.tracker.export_csv(self.filepath)
        with open(self.filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["category"] == "food"
        assert rows[0]["description"] == "pizza"
        assert float(rows[0]["amount"]) == pytest.approx(10.0)

    def test_export_csv_multiple_rows(self):
        self.tracker.add_expense(10.0, "food", "a")
        self.tracker.add_expense(20.0, "transport", "b")
        self.tracker.export_csv(self.filepath)
        with open(self.filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2

    def test_export_empty_tracker(self):
        self.tracker.export_csv(self.filepath)
        assert os.path.exists(self.filepath)
        with open(self.filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert rows == []
