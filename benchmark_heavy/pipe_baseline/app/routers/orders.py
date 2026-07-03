"""Order HTTP endpoint'leri."""
import sqlite3

from fastapi import APIRouter, Depends, Response

from app.db import get_conn
from app.schemas.order import OrderCreate
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


def db() -> sqlite3.Connection:
    return get_conn()


@router.post("", status_code=201)
def create(body: OrderCreate, conn: sqlite3.Connection = Depends(db)):
    return order_service.create_order(conn, body.items)


@router.get("/{order_id}")
def get(order_id: int, conn: sqlite3.Connection = Depends(db)):
    return order_service.get_order(conn, order_id)


@router.post("/{order_id}/cancel")
def cancel(order_id: int, conn: sqlite3.Connection = Depends(db)):
    return order_service.cancel_order(conn, order_id)


