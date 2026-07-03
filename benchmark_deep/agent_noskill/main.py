"""Envanter & Sipariş Yönetim REST API'si (FastAPI + stdlib sqlite3)."""
from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

# --- DB configuration -------------------------------------------------------
# DB path is read from env so tests can point at an isolated / in-memory DB.
DB_PATH = os.environ.get("INVENTORY_DB", "inventory.db")

# A single shared connection is used when the DB is in-memory, otherwise each
# request opens its own connection. ":memory:" databases vanish per-connection,
# so we keep one connection alive for that case.
_shared_conn: Optional[sqlite3.Connection] = None


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            sku         TEXT NOT NULL UNIQUE,
            price_cents INTEGER NOT NULL,
            stock       INTEGER NOT NULL,
            category    TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            status     TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_items (
            order_id         INTEGER NOT NULL,
            product_id       INTEGER NOT NULL,
            quantity         INTEGER NOT NULL,
            unit_price_cents INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        """
    )
    conn.commit()


def get_conn() -> sqlite3.Connection:
    """Return a connection. For :memory: reuse one shared connection."""
    global _shared_conn
    if DB_PATH == ":memory:":
        if _shared_conn is None:
            _shared_conn = _make_conn()
        return _shared_conn
    if _shared_conn is None:
        _shared_conn = _make_conn()
    return _shared_conn


def reset_db() -> None:
    """Drop and recreate all tables — handy for test isolation."""
    conn = get_conn()
    conn.executescript(
        "DROP TABLE IF EXISTS order_items;"
        "DROP TABLE IF EXISTS orders;"
        "DROP TABLE IF EXISTS products;"
    )
    conn.commit()
    init_db()


# --- Schemas ----------------------------------------------------------------
class ProductIn(BaseModel):
    name: str
    sku: str
    price_cents: int = Field(..., ge=0)
    stock: int = Field(..., ge=0)
    category: str


class ProductPatch(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    price_cents: Optional[int] = Field(default=None, ge=0)
    stock: Optional[int] = Field(default=None, ge=0)
    category: Optional[str] = None


class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)


class OrderIn(BaseModel):
    items: list[OrderItemIn] = Field(..., min_length=1)


# --- App --------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Inventory & Order API", lifespan=lifespan)


def db() -> sqlite3.Connection:
    return get_conn()


def _product_dict(row: sqlite3.Row) -> dict:
    return dict(row)


# --- Products ---------------------------------------------------------------
@app.post("/products", status_code=201)
def create_product(body: ProductIn, conn: sqlite3.Connection = Depends(db)):
    try:
        cur = conn.execute(
            "INSERT INTO products (name, sku, price_cents, stock, category) "
            "VALUES (?, ?, ?, ?, ?)",
            (body.name, body.sku, body.price_cents, body.stock, body.category),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="sku already exists")
    row = conn.execute(
        "SELECT * FROM products WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return _product_dict(row)


@app.get("/products")
def list_products(
    category: Optional[str] = None,
    limit: int = Query(default=50, ge=0),
    offset: int = Query(default=0, ge=0),
    conn: sqlite3.Connection = Depends(db),
):
    if category is not None:
        rows = conn.execute(
            "SELECT * FROM products WHERE category = ? "
            "ORDER BY id LIMIT ? OFFSET ?",
            (category, limit, offset),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM products ORDER BY id LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [_product_dict(r) for r in rows]


@app.get("/products/{product_id}")
def get_product(product_id: int, conn: sqlite3.Connection = Depends(db)):
    row = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="product not found")
    return _product_dict(row)


@app.patch("/products/{product_id}")
def patch_product(
    product_id: int,
    body: ProductPatch,
    conn: sqlite3.Connection = Depends(db),
):
    row = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="product not found")
    fields = body.model_dump(exclude_unset=True)
    if fields:
        cols = ", ".join(f"{k} = ?" for k in fields)
        try:
            conn.execute(
                f"UPDATE products SET {cols} WHERE id = ?",
                (*fields.values(), product_id),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="sku already exists")
    row = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    return _product_dict(row)


@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, conn: sqlite3.Connection = Depends(db)):
    row = conn.execute(
        "SELECT id FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="product not found")
    ref = conn.execute(
        "SELECT 1 FROM order_items WHERE product_id = ? LIMIT 1", (product_id,)
    ).fetchone()
    if ref is not None:
        raise HTTPException(
            status_code=409, detail="product referenced by an order"
        )
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    return None


# --- Orders -----------------------------------------------------------------
def _order_response(conn: sqlite3.Connection, order_id: int) -> dict:
    order = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    items = conn.execute(
        "SELECT product_id, quantity, unit_price_cents "
        "FROM order_items WHERE order_id = ?",
        (order_id,),
    ).fetchall()
    item_list = [dict(i) for i in items]
    total = sum(i["quantity"] * i["unit_price_cents"] for i in item_list)
    return {
        "id": order["id"],
        "status": order["status"],
        "created_at": order["created_at"],
        "items": item_list,
        "total_cents": total,
    }


@app.post("/orders", status_code=201)
def create_order(body: OrderIn, conn: sqlite3.Connection = Depends(db)):
    # Validate products exist and stock is sufficient BEFORE any mutation.
    snapshots = []  # (product_id, quantity, unit_price_cents)
    for item in body.items:
        product = conn.execute(
            "SELECT id, price_cents, stock FROM products WHERE id = ?",
            (item.product_id,),
        ).fetchone()
        if product is None:
            raise HTTPException(
                status_code=404,
                detail=f"product {item.product_id} not found",
            )
        snapshots.append((product, item.quantity))

    # Aggregate requested quantity per product so duplicate lines for the
    # same product can't oversell.
    requested: dict[int, int] = {}
    for product, qty in snapshots:
        requested[product["id"]] = requested.get(product["id"], 0) + qty
    for product, _ in snapshots:
        if requested[product["id"]] > product["stock"]:
            raise HTTPException(status_code=409, detail="insufficient stock")

    created_at = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO orders (status, created_at) VALUES ('pending', ?)",
        (created_at,),
    )
    order_id = cur.lastrowid
    for product, qty in snapshots:
        conn.execute(
            "INSERT INTO order_items "
            "(order_id, product_id, quantity, unit_price_cents) "
            "VALUES (?, ?, ?, ?)",
            (order_id, product["id"], qty, product["price_cents"]),
        )
        conn.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ?",
            (qty, product["id"]),
        )
    conn.commit()
    return _order_response(conn, order_id)


@app.get("/orders/{order_id}")
def get_order(order_id: int, conn: sqlite3.Connection = Depends(db)):
    order = conn.execute(
        "SELECT id FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return _order_response(conn, order_id)


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int, conn: sqlite3.Connection = Depends(db)):
    order = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order["status"] == "cancelled":
        raise HTTPException(status_code=409, detail="order already cancelled")
    items = conn.execute(
        "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
        (order_id,),
    ).fetchall()
    for item in items:
        conn.execute(
            "UPDATE products SET stock = stock + ? WHERE id = ?",
            (item["quantity"], item["product_id"]),
        )
    conn.execute(
        "UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,)
    )
    conn.commit()
    return _order_response(conn, order_id)


# --- Reports ----------------------------------------------------------------
@app.get("/reports/low-stock")
def low_stock(
    threshold: int = 10, conn: sqlite3.Connection = Depends(db)
):
    rows = conn.execute(
        "SELECT * FROM products WHERE stock <= ? ORDER BY id", (threshold,)
    ).fetchall()
    return [_product_dict(r) for r in rows]


@app.get("/reports/revenue-by-category")
def revenue_by_category(conn: sqlite3.Connection = Depends(db)):
    rows = conn.execute(
        """
        SELECT p.category AS category,
               SUM(oi.quantity * oi.unit_price_cents) AS revenue
        FROM order_items oi
        JOIN orders o   ON o.id = oi.order_id
        JOIN products p ON p.id = oi.product_id
        WHERE o.status != 'cancelled'
        GROUP BY p.category
        """
    ).fetchall()
    return {r["category"]: r["revenue"] for r in rows}
