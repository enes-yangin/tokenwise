"""Veritabanı katmanı — paylaşılan bağlantı + şema kaydı.

YENİ BİR KAYNAK EKLERKEN: model modülünü `_MODEL_MODULES` listesine ekle ki
şeması init sırasında kurulsun.
"""
import importlib
import os
import sqlite3
from typing import Optional

DB_PATH = os.environ.get("APP_DB", "app.db")

_shared: Optional[sqlite3.Connection] = None

# init_db bu modülleri import eder; her model modülü SCHEMA sabitini expose eder.
_MODEL_MODULES = [
    "app.models.user",
    "app.models.product",
    "app.models.order",
]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_conn() -> sqlite3.Connection:
    """Tek paylaşılan bağlantı (:memory: testleri için şart)."""
    global _shared
    if _shared is None:
        _shared = _connect()
    return _shared


def init_db() -> None:
    conn = get_conn()
    for mod_name in _MODEL_MODULES:
        mod = importlib.import_module(mod_name)
        conn.executescript(mod.SCHEMA)
    conn.commit()


def reset_for_tests() -> None:
    """Test izolasyonu: bağlantıyı sıfırla."""
    global _shared
    if _shared is not None:
        _shared.close()
    _shared = None
