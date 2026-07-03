"""Order HTTP endpoint'leri."""
import sqlite3

from fastapi import APIRouter, Depends, Response

from app.db import get_conn
from app.schemas.order import OrderIn
from app.services import order_service

router = APIRouter(tags=["orders"])


def db() -> sqlite3.Connection:
    return get_conn()


@router.post("/orders", status_code=201)
def create(body: OrderIn, conn: sqlite3.Connection = Depends(db)):
    return order_service.create_order(conn, body.items)


@router.get("/orders/{order_id}")
def get(order_id: int, conn: sqlite3.Connection = Depends(db)):
    return order_service.get_order(conn, order_id)


@router.post("/orders/{order_id}/cancel")
def cancel(order_id: int, conn: sqlite3.Connection = Depends(db)):
    return order_service.cancel_order(conn, order_id)


@router.get("/reports/revenue-by-category")
def revenue_by_category(conn: sqlite3.Connection = Depends(db)):
    return order_service.get_revenue_by_category(conn)
