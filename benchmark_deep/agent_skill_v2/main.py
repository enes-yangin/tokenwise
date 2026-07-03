import os
import sqlite3
from datetime import datetime, timezone

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field, conint

DB_PATH = os.environ.get("DB_PATH", "inventory.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
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


# ---------- Schemas ----------
class ProductIn(BaseModel):
    name: str
    sku: str
    price_cents: conint(ge=0)
    stock: conint(ge=0)
    category: str


class ProductPatch(BaseModel):
    name: str | None = None
    sku: str | None = None
    price_cents: conint(ge=0) | None = None
    stock: conint(ge=0) | None = None
    category: str | None = None


class OrderItemIn(BaseModel):
    product_id: int
    quantity: conint(gt=0)


class OrderIn(BaseModel):
    items: list[OrderItemIn] = Field(min_length=1)


# ---------- App factory ----------
app = FastAPI()
# Single shared connection for the app's lifetime (TestClient is single-threaded;
# file-mode is fine too). Created at import so each importlib.reload -> fresh DB.
conn = get_conn()
init_schema(conn)


def product_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def get_product_row(pid: int):
    return conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()


# ---------- Products ----------
@app.post("/products", status_code=201)
def create_product(p: ProductIn):
    try:
        cur = conn.execute(
            "INSERT INTO products (name, sku, price_cents, stock, category) VALUES (?,?,?,?,?)",
            (p.name, p.sku, p.price_cents, p.stock, p.category),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="sku already exists")
    return product_dict(get_product_row(cur.lastrowid))


@app.get("/products")
def list_products(
    category: str | None = None,
    limit: int = Query(50, ge=0),
    offset: int = Query(0, ge=0),
):
    sql = "SELECT * FROM products"
    args: list = []
    if category is not None:
        sql += " WHERE category=?"
        args.append(category)
    sql += " ORDER BY id LIMIT ? OFFSET ?"
    args += [limit, offset]
    return [product_dict(r) for r in conn.execute(sql, args).fetchall()]


@app.get("/products/{pid}")
def get_product(pid: int):
    row = get_product_row(pid)
    if row is None:
        raise HTTPException(status_code=404, detail="not found")
    return product_dict(row)


@app.patch("/products/{pid}")
def patch_product(pid: int, patch: ProductPatch):
    if get_product_row(pid) is None:
        raise HTTPException(status_code=404, detail="not found")
    fields = patch.model_dump(exclude_unset=True)
    if fields:
        sets = ", ".join(f"{k}=?" for k in fields)
        try:
            conn.execute(f"UPDATE products SET {sets} WHERE id=?", [*fields.values(), pid])
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="sku already exists")
    return product_dict(get_product_row(pid))


@app.delete("/products/{pid}", status_code=204)
def delete_product(pid: int):
    if get_product_row(pid) is None:
        raise HTTPException(status_code=404, detail="not found")
    ref = conn.execute(
        "SELECT 1 FROM order_items WHERE product_id=? LIMIT 1", (pid,)
    ).fetchone()
    if ref is not None:
        raise HTTPException(status_code=409, detail="product referenced by an order")
    conn.execute("DELETE FROM products WHERE id=?", (pid,))
    conn.commit()
    return Response(status_code=204)


# ---------- Orders ----------
def serialize_order(oid: int) -> dict:
    order = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if order is None:
        return None
    items = conn.execute(
        "SELECT product_id, quantity, unit_price_cents FROM order_items WHERE order_id=?",
        (oid,),
    ).fetchall()
    items = [dict(i) for i in items]
    total = sum(i["unit_price_cents"] * i["quantity"] for i in items)
    return {
        "id": order["id"],
        "status": order["status"],
        "created_at": order["created_at"],
        "items": items,
        "total_cents": total,
    }


@app.post("/orders", status_code=201)
def create_order(order: OrderIn):
    # Validate everything BEFORE mutating any stock (atomicity).
    resolved = []
    for it in order.items:
        prod = get_product_row(it.product_id)
        if prod is None:
            raise HTTPException(status_code=404, detail=f"product {it.product_id} not found")
        resolved.append((prod, it.quantity))
    for prod, qty in resolved:
        if prod["stock"] < qty:
            raise HTTPException(status_code=409, detail="insufficient stock")
    created_at = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO orders (status, created_at) VALUES ('pending', ?)", (created_at,)
    )
    oid = cur.lastrowid
    for prod, qty in resolved:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents) VALUES (?,?,?,?)",
            (oid, prod["id"], qty, prod["price_cents"]),
        )
        conn.execute(
            "UPDATE products SET stock = stock - ? WHERE id=?", (qty, prod["id"])
        )
    conn.commit()
    return serialize_order(oid)


@app.get("/orders/{oid}")
def get_order(oid: int):
    o = serialize_order(oid)
    if o is None:
        raise HTTPException(status_code=404, detail="not found")
    return o


@app.post("/orders/{oid}/cancel")
def cancel_order(oid: int):
    order = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if order is None:
        raise HTTPException(status_code=404, detail="not found")
    if order["status"] == "cancelled":
        raise HTTPException(status_code=409, detail="already cancelled")
    items = conn.execute(
        "SELECT product_id, quantity FROM order_items WHERE order_id=?", (oid,)
    ).fetchall()
    for i in items:
        conn.execute(
            "UPDATE products SET stock = stock + ? WHERE id=?",
            (i["quantity"], i["product_id"]),
        )
    conn.execute("UPDATE orders SET status='cancelled' WHERE id=?", (oid,))
    conn.commit()
    return serialize_order(oid)


# ---------- Reports ----------
@app.get("/reports/low-stock")
def low_stock(threshold: int = 10):
    rows = conn.execute(
        "SELECT * FROM products WHERE stock <= ? ORDER BY id", (threshold,)
    ).fetchall()
    return [product_dict(r) for r in rows]


@app.get("/reports/revenue-by-category")
def revenue_by_category():
    rows = conn.execute(
        """
        SELECT p.category AS category,
               SUM(oi.unit_price_cents * oi.quantity) AS revenue
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        JOIN products p ON p.id = oi.product_id
        WHERE o.status != 'cancelled'
        GROUP BY p.category
        """
    ).fetchall()
    return {r["category"]: r["revenue"] for r in rows}
