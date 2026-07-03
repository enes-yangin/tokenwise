"""Reports HTTP endpoint'leri."""
import sqlite3

from fastapi import APIRouter, Depends

from app.db import get_conn
from app.services import order_service

router = APIRouter(prefix="/reports", tags=["reports"])


def db() -> sqlite3.Connection:
    return get_conn()


@router.get("/revenue-by-category")
def revenue_by_category(conn: sqlite3.Connection = Depends(db)):
    """Kategori bazında gelir raporu."""
    return order_service.get_revenue_by_category(conn)
