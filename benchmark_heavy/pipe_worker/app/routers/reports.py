"""Reports HTTP endpoint'leri."""
import sqlite3

from fastapi import APIRouter, Depends

from app.db import get_conn
from app.services import order_service

router = APIRouter(tags=["reports"])


def db() -> sqlite3.Connection:
    return get_conn()


@router.get("/reports/revenue-by-category")
def revenue_by_category(conn: sqlite3.Connection = Depends(db)):
    return order_service.get_revenue_by_category(conn)
