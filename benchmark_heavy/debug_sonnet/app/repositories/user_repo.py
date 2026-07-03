"""User veri erişim katmanı."""
import sqlite3

from app.models import user as user_model


def create(conn: sqlite3.Connection, data: dict) -> dict:
    cur = conn.execute(
        "INSERT INTO users (email, name) VALUES (?, ?)",
        (data["email"], data["name"]),
    )
    conn.commit()
    return get(conn, cur.lastrowid)


def get(conn: sqlite3.Connection, user_id: int):
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return user_model.to_dict(row) if row else None


def get_by_email(conn: sqlite3.Connection, email: str):
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return user_model.to_dict(row) if row else None


def list_(conn: sqlite3.Connection, limit=50, offset=0) -> list:
    rows = conn.execute(
        "SELECT * FROM users ORDER BY id LIMIT ? OFFSET ?", (limit, offset)
    ).fetchall()
    return [user_model.to_dict(r) for r in rows]
