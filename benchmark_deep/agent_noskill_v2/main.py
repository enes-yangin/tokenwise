import os
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

DB_PATH = os.environ.get("DB_PATH", "inventory.db")

# A shared in-memory connection (used when DB_PATH == ":memory:") must persist
# for the process lifetime, otherwise the schema vanishes between connections.
_memory_conn: Optional[sqlite3.Connection] = None


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn():
    global _memory_conn
    if DB_PATH == ":memory:":
        if _memory_conn is None:
            _memory_conn = _make_conn()
            _init_schema(_memory_conn)
        yield _memory_conn
        return
    conn = _make_conn()
    try:
        yield conn
    finally:
        conn.close()


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT NOT NULL UNIQUE,
            price_cents INTEGER NOT NULL,
            stock INTEGER NOT NULL,
            category TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price_cents INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        """
    )
    conn.commit()


def init_db() -> None:
    with get_conn() as conn:
        _init_schema(conn)


# ---------- Schemas ----------
class ProductCreate(BaseModel):
    name: str
    sku: str
    price_cents: int = Field(ge=0)
    stock: int = Field(ge=0)
    category: str


class ProductPatch(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    price_cents: Optional[int] = Field(default=None, ge=0)
    stock: Optional[int] = Field(default=None, ge=0)
    category: Optional[str] = None


class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    items: list[OrderItemIn] = Field(min_length=1)


# ---------- App ----------
app = FastAPI(title="Inventory & Order API")


@app.on_event("startup")
def _startup() -> None:
    init_db()


def _product_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "sku": row["sku"],
        "price_cents": row["price_cents"],
        "stock": row["stock"],
        "category": row["category"],
    }


def _order_dict(conn: sqlite3.Connection, order_row: sqlite3.Row) -> dict:
    items = conn.execute(
        "SELECT product_id, quantity, unit_price_cents FROM order_items WHERE order_id = ?",
        (order_row["id"],),
    ).fetchall()
    item_list = [
        {
            "product_id": it["product_id"],
            "quantity": it["quantity"],
            "unit_price_cents": it["unit_price_cents"],
        }
        for it in items
    ]
    total = sum(it["quantity"] * it["unit_price_cents"] for it in items)
    return {
        "id": order_row["id"],
        "status": order_row["status"],
        "created_at": order_row["created_at"],
        "items": item_list,
        "total_cents": total,
    }


# ---------- Products ----------
@app.post("/products", status_code=201)
def create_product(payload: ProductCreate):
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO products (name, sku, price_cents, stock, category) VALUES (?, ?, ?, ?, ?)",
                (payload.name, payload.sku, payload.price_cents, payload.stock, payload.category),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="sku already exists")
        row = conn.execute("SELECT * FROM products WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _product_dict(row)


@app.get("/products")
def list_products(
    category: Optional[str] = None,
    limit: int = Query(50, ge=0),
    offset: int = Query(0, ge=0),
):
    with get_conn() as conn:
        if category is not None:
            rows = conn.execute(
                "SELECT * FROM products WHERE category = ? ORDER BY id LIMIT ? OFFSET ?",
                (category, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM products ORDER BY id LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [_product_dict(r) for r in rows]


@app.get("/products/{product_id}")
def get_product(product_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="product not found")
        return _product_dict(row)


@app.patch("/products/{product_id}")
def patch_product(product_id: int, payload: ProductPatch):
    fields = payload.model_dump(exclude_unset=True)
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="product not found")
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
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return _product_dict(row)


@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="product not found")
        ref = conn.execute(
            "SELECT 1 FROM order_items WHERE product_id = ? LIMIT 1", (product_id,)
        ).fetchone()
        if ref is not None:
            raise HTTPException(status_code=409, detail="product referenced by an order")
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        return Response(status_code=204)


# ---------- Orders ----------
@app.post("/orders", status_code=201)
def create_order(payload: OrderCreate):
    with get_conn() as conn:
        # Load all referenced products, validate existence and stock first (atomic).
        wanted: dict[int, int] = {}
        for it in payload.items:
            wanted[it.product_id] = wanted.get(it.product_id, 0) + it.quantity

        products: dict[int, sqlite3.Row] = {}
        for pid in wanted:
            prow = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
            if prow is None:
                raise HTTPException(status_code=404, detail=f"product {pid} not found")
            products[pid] = prow

        for pid, qty in wanted.items():
            if products[pid]["stock"] < qty:
                raise HTTPException(status_code=409, detail=f"insufficient stock for product {pid}")

        created_at = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            "INSERT INTO orders (status, created_at) VALUES (?, ?)", ("pending", created_at)
        )
        order_id = cur.lastrowid

        for it in payload.items:
            unit_price = products[it.product_id]["price_cents"]
            conn.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents) VALUES (?, ?, ?, ?)",
                (order_id, it.product_id, it.quantity, unit_price),
            )
        for pid, qty in wanted.items():
            conn.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (qty, pid))
        conn.commit()

        order_row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return _order_dict(conn, order_row)


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="order not found")
        return _order_dict(conn, row)


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="order not found")
        if row["status"] == "cancelled":
            raise HTTPException(status_code=409, detail="order already cancelled")
        items = conn.execute(
            "SELECT product_id, quantity FROM order_items WHERE order_id = ?", (order_id,)
        ).fetchall()
        for it in items:
            conn.execute(
                "UPDATE products SET stock = stock + ? WHERE id = ?",
                (it["quantity"], it["product_id"]),
            )
        conn.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
        conn.commit()
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return _order_dict(conn, row)


# ---------- Reports ----------
@app.get("/reports/low-stock")
def low_stock(threshold: int = 10):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM products WHERE stock <= ? ORDER BY id", (threshold,)
        ).fetchall()
        return [_product_dict(r) for r in rows]


@app.get("/reports/revenue-by-category")
def revenue_by_category():
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT p.category AS category,
                   SUM(oi.quantity * oi.unit_price_cents) AS revenue
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            JOIN products p ON p.id = oi.product_id
            WHERE o.status != 'cancelled'
            GROUP BY p.category
            """
        ).fetchall()
        return {r["category"]: r["revenue"] for r in rows}
