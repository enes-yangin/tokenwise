"""User iş mantığı."""
import sqlite3

from fastapi import HTTPException

from app.repositories import user_repo


def create_user(conn: sqlite3.Connection, data: dict) -> dict:
    if user_repo.get_by_email(conn, data["email"]):
        raise HTTPException(status_code=409, detail="email already exists")
    return user_repo.create(conn, data)


def get_user(conn: sqlite3.Connection, user_id: int) -> dict:
    user = user_repo.get(conn, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return user


def list_users(conn, limit=50, offset=0) -> list:
    return user_repo.list_(conn, limit, offset)
