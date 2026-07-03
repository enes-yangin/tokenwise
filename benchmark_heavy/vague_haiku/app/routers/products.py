"""Product HTTP endpoint'leri."""
import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response

from app.db import get_conn
from app.schemas.product import ProductIn, ProductPatch
from app.services import product_service

router = APIRouter(prefix="/products", tags=["products"])


def db() -> sqlite3.Connection:
    return get_conn()


@router.post("", status_code=201)
def create(body: ProductIn, conn: sqlite3.Connection = Depends(db)):
    return product_service.create_product(conn, body.model_dump())


@router.get("")
def list_products(
    category: Optional[str] = None,
    limit: int = Query(50, ge=0),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(db),
):
    return product_service.list_products(conn, category, limit, offset)


@router.get("/{product_id}")
def get(product_id: int, conn: sqlite3.Connection = Depends(db)):
    return product_service.get_product(conn, product_id)


@router.patch("/{product_id}")
def patch(product_id: int, body: ProductPatch, conn: sqlite3.Connection = Depends(db)):
    return product_service.update_product(
        conn, product_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/{product_id}", status_code=204)
def delete(product_id: int, conn: sqlite3.Connection = Depends(db)):
    product_service.delete_product(conn, product_id)
    return Response(status_code=204)
