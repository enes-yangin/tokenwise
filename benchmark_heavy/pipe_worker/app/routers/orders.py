"""Order HTTP endpoint'leri."""
import sqlite3

from fastapi import APIRouter, Depends

from app.db import get_conn
from app.schemas.order import OrderIn
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


def db() -> sqlite3.Connection:
    return get_conn()


@router.post("", status_code=201)
def create_order(body: OrderIn, conn: sqlite3.Connection = Depends(db)):
    return order_service.create_order(conn, body.model_dump())


@router.get("/{order_id}")
def get_order(order_id: int, conn: sqlite3.Connection = Depends(db)):
    return order_service.get_order(conn, order_id)


@router.post("/{order_id}/cancel")
def cancel_order(order_id: int, conn: sqlite3.Connection = Depends(db)):
    return order_service.cancel_order(conn, order_id)
