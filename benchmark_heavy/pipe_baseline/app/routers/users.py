"""User HTTP endpoint'leri."""
import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.db import get_conn
from app.schemas.user import UserIn
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


def db() -> sqlite3.Connection:
    return get_conn()


@router.post("", status_code=201)
def create(body: UserIn, conn: sqlite3.Connection = Depends(db)):
    return user_service.create_user(conn, body.model_dump())


@router.get("")
def list_users(
    limit: int = Query(50, ge=0),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(db),
):
    return user_service.list_users(conn, limit, offset)


@router.get("/{user_id}")
def get(user_id: int, conn: sqlite3.Connection = Depends(db)):
    return user_service.get_user(conn, user_id)
