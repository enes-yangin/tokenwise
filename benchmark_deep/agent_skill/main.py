import os
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field, conint, constr

DB_PATH = os.environ.get("DATABASE_URL", "inventory.db")

SCHEMA = """
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

# A single shared in-memory connection must be reused across requests, because a
# fresh :memory: connection gets its own empty database. For file DBs we open
# per-call connections.
_shared_memory_conn: Optional[sqlite3.Connection] = None


def _is_memory(path: str) -> bool:
    return path == ":memory:" or path.startswith("file::memory:")


def _new_connection(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    global _shared_memory_conn
    if _is_memory(DB_PATH):
        _shared_memory_conn = _new_connection(DB_PATH)
        _shared_memory_conn.executescript(SCHEMA)
    else:
        conn = _new_connection(DB_PATH)
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()


@contextmanager
def get_conn():
    if _is_memory(DB_PATH):
        # Reuse the single shared connection; do not close it.
        assert _shared_memory_conn is not None, "init_db() not called"
        yield _shared_memory_conn
    else:
        conn = _new_connection(DB_PATH)
        try:
            yield conn
        finally:
            conn.close()


def db_dep():
    with get_conn() as conn:
        yield conn


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class ProductIn(BaseModel):
    name: constr(min_length=1)
    sku: constr(min_length=1)
    price_cents: conint(ge=0)
    stock: conint(ge=0)
    category: constr(min_length=1)


class ProductPatch(BaseModel):
    name: Optional[constr(min_length=1)] = None
    sku: Optional[constr(min_length=1)] = None
    price_cents: Optional[conint(ge=0)] = None
    stock: Optional[conint(ge=0)] = None
    category: Optional[constr(min_length=1)] = None


class OrderItemIn(BaseModel):
    product_id: int
    quantity: conint(gt=0)


class OrderIn(BaseModel):
    items: list[OrderItemIn] = Field(min_length=1)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def product_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "sku": row["sku"],
        "price_cents": row["price_cents"],
        "stock": row["stock"],
        "category": row["category"],
    }


def order_response(conn: sqlite3.Connection, order_id: int) -> dict:
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    items = conn.execute(
        "SELECT product_id, quantity, unit_price_cents FROM order_items WHERE order_id = ?",
        (order_id,),
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
        "id": order["id"],
        "status": order["status"],
        "created_at": order["created_at"],
        "items": item_list,
        "total_cents": total,
    }


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


# ---- Products ---- #
@app.post("/products", status_code=201)
def create_product(body: ProductIn, conn: sqlite3.Connection = Depends(db_dep)):
    existing = conn.execute(
        "SELECT 1 FROM products WHERE sku = ?", (body.sku,)
    ).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="sku already exists")
    cur = conn.execute(
        "INSERT INTO products (name, sku, price_cents, stock, category) "
        "VALUES (?, ?, ?, ?, ?)",
        (body.name, body.sku, body.price_cents, body.stock, body.category),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM products WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return product_dict(row)


@app.get("/products")
def list_products(
    conn: sqlite3.Connection = Depends(db_dep),
    category: Optional[str] = None,
    limit: int = Query(50, ge=0),
    offset: int = Query(0, ge=0),
):
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
    return [product_dict(r) for r in rows]


@app.get("/products/{product_id}")
def get_product(product_id: int, conn: sqlite3.Connection = Depends(db_dep)):
    row = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="product not found")
    return product_dict(row)


@app.patch("/products/{product_id}")
def patch_product(
    product_id: int,
    body: ProductPatch,
    conn: sqlite3.Connection = Depends(db_dep),
):
    row = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="product not found")
    fields = body.model_dump(exclude_unset=True)
    if "sku" in fields and fields["sku"] != row["sku"]:
        dup = conn.execute(
            "SELECT 1 FROM products WHERE sku = ? AND id != ?",
            (fields["sku"], product_id),
        ).fetchone()
        if dup:
            raise HTTPException(status_code=409, detail="sku already exists")
    if fields:
        cols = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE products SET {cols} WHERE id = ?",
            (*fields.values(), product_id),
        )
        conn.commit()
    row = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    return product_dict(row)


@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, conn: sqlite3.Connection = Depends(db_dep)):
    row = conn.execute(
        "SELECT 1 FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="product not found")
    referenced = conn.execute(
        "SELECT 1 FROM order_items WHERE product_id = ?", (product_id,)
    ).fetchone()
    if referenced:
        raise HTTPException(
            status_code=409, detail="product referenced by an order"
        )
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    return Response(status_code=204)


# ---- Orders ---- #
@app.post("/orders", status_code=201)
def create_order(body: OrderIn, conn: sqlite3.Connection = Depends(db_dep)):
    # Resolve products and validate atomically before any mutation.
    snapshots = []  # (product_id, quantity, unit_price_cents, current_stock)
    for item in body.items:
        prod = conn.execute(
            "SELECT * FROM products WHERE id = ?", (item.product_id,)
        ).fetchone()
        if prod is None:
            raise HTTPException(
                status_code=404, detail=f"product {item.product_id} not found"
            )
        snapshots.append((prod, item.quantity))

    # Aggregate quantities per product so duplicate lines are checked together.
    needed: dict[int, int] = {}
    for prod, qty in snapshots:
        needed[prod["id"]] = needed.get(prod["id"], 0) + qty
    for prod, _ in snapshots:
        if prod["stock"] < needed[prod["id"]]:
            raise HTTPException(status_code=409, detail="insufficient stock")

    created_at = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO orders (status, created_at) VALUES ('pending', ?)",
        (created_at,),
    )
    order_id = cur.lastrowid
    for prod, qty in snapshots:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents) "
            "VALUES (?, ?, ?, ?)",
            (order_id, prod["id"], qty, prod["price_cents"]),
        )
        conn.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ?",
            (qty, prod["id"]),
        )
    conn.commit()
    return order_response(conn, order_id)


@app.get("/orders/{order_id}")
def get_order(order_id: int, conn: sqlite3.Connection = Depends(db_dep)):
    return order_response(conn, order_id)


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int, conn: sqlite3.Connection = Depends(db_dep)):
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
    for it in items:
        conn.execute(
            "UPDATE products SET stock = stock + ? WHERE id = ?",
            (it["quantity"], it["product_id"]),
        )
    conn.execute(
        "UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,)
    )
    conn.commit()
    return order_response(conn, order_id)


# ---- Reports ---- #
@app.get("/reports/low-stock")
def low_stock(
    conn: sqlite3.Connection = Depends(db_dep),
    threshold: int = 10,
):
    rows = conn.execute(
        "SELECT * FROM products WHERE stock <= ? ORDER BY id", (threshold,)
    ).fetchall()
    return [product_dict(r) for r in rows]


@app.get("/reports/revenue-by-category")
def revenue_by_category(conn: sqlite3.Connection = Depends(db_dep)):
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
