import csv
import os
import tempfile

import pytest

from expense_tracker import Expense, ExpenseTracker


def make_tracker(*items):
    t = ExpenseTracker()
    for amount, category, description in items:
        t.add_expense(amount, category, description)
    return t


# --- add_expense ---

def test_add_expense_returns_expense():
    t = ExpenseTracker()
    e = t.add_expense(10.0, "food", "lunch")
    assert isinstance(e, Expense)
    assert e.amount == 10.0
    assert e.category == "food"
    assert e.description == "lunch"


def test_add_expense_assigns_unique_ids():
    t = ExpenseTracker()
    e1 = t.add_expense(5.0, "food", "a")
    e2 = t.add_expense(5.0, "food", "b")
    assert e1.id != e2.id


def test_add_expense_zero_raises():
    t = ExpenseTracker()
    with pytest.raises(ValueError):
        t.add_expense(0, "food", "x")


def test_add_expense_negative_raises():
    t = ExpenseTracker()
    with pytest.raises(ValueError):
        t.add_expense(-1.0, "food", "x")


def test_add_expense_empty_category_raises():
    t = ExpenseTracker()
    with pytest.raises(ValueError):
        t.add_expense(5.0, "", "x")


def test_add_expense_date_set():
    from datetime import datetime
    t = ExpenseTracker()
    before = datetime.now()
    e = t.add_expense(1.0, "misc", "t")
    after = datetime.now()
    assert before <= e.date <= after


# --- list_expenses ---

def test_list_expenses_all():
    t = make_tracker((10, "food", "a"), (20, "travel", "b"))
    assert len(t.list_expenses()) == 2


def test_list_expenses_by_category():
    t = make_tracker((10, "food", "a"), (20, "travel", "b"), (5, "food", "c"))
    food = t.list_expenses("food")
    assert len(food) == 2
    assert all(e.category == "food" for e in food)


def test_list_expenses_unknown_category_empty():
    t = make_tracker((10, "food", "a"))
    assert t.list_expenses("travel") == []


def test_list_expenses_returns_copy():
    t = make_tracker((10, "food", "a"))
    result = t.list_expenses()
    result.clear()
    assert len(t.list_expenses()) == 1


# --- total_by_category ---

def test_total_by_category_single():
    t = make_tracker((10, "food", "a"), (5, "food", "b"))
    totals = t.total_by_category()
    assert totals == {"food": 15.0}


def test_total_by_category_multiple():
    t = make_tracker((10, "food", "a"), (20, "travel", "b"), (5, "food", "c"))
    totals = t.total_by_category()
    assert totals["food"] == pytest.approx(15.0)
    assert totals["travel"] == pytest.approx(20.0)


def test_total_by_category_empty():
    t = ExpenseTracker()
    assert t.total_by_category() == {}


# --- export_csv ---

def test_export_csv_creates_file():
    t = make_tracker((10, "food", "lunch"))
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        path = f.name
    try:
        t.export_csv(path)
        assert os.path.exists(path)
    finally:
        os.unlink(path)


def test_export_csv_headers_and_rows():
    t = make_tracker((10.5, "food", "lunch"), (20.0, "travel", "train"))
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        path = f.name
    try:
        t.export_csv(path)
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert set(rows[0].keys()) == {"amount", "category", "description", "date"}
        assert float(rows[0]["amount"]) == pytest.approx(10.5)
        assert rows[0]["category"] == "food"
        assert rows[1]["category"] == "travel"
    finally:
        os.unlink(path)


def test_export_csv_empty_tracker():
    t = ExpenseTracker()
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        path = f.name
    try:
        t.export_csv(path)
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert rows == []
    finally:
        os.unlink(path)
