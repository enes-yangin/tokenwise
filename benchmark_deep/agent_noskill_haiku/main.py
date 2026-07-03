import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

# --- Database ---
DB_PATH = os.getenv("DB_PATH", "inventory.db")


@contextmanager
def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize database tables."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Drop tables if they exist (for clean slate in tests)
        cursor.execute("DROP TABLE IF EXISTS OrderItem")
        cursor.execute('DROP TABLE IF EXISTS "Order"')
        cursor.execute("DROP TABLE IF EXISTS Product")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Product (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sku TEXT NOT NULL UNIQUE,
                price_cents INTEGER NOT NULL,
                stock INTEGER NOT NULL,
                category TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "Order" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS OrderItem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price_cents INTEGER NOT NULL,
                FOREIGN KEY (order_id) REFERENCES "Order"(id),
                FOREIGN KEY (product_id) REFERENCES Product(id)
            )
        """)

        conn.commit()


# --- Pydantic Models ---
class ProductCreate(BaseModel):
    name: str
    sku: str
    price_cents: int
    stock: int
    category: str


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price_cents: Optional[int] = None
    stock: Optional[int] = None
    category: Optional[str] = None


class ProductResponse(BaseModel):
    id: int
    name: str
    sku: str
    price_cents: int
    stock: int
    category: str


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int


class OrderItemResponse(BaseModel):
    product_id: int
    quantity: int
    unit_price_cents: int


class OrderCreate(BaseModel):
    items: List[OrderItemCreate]


class OrderResponse(BaseModel):
    id: int
    status: str
    created_at: str
    items: List[OrderItemResponse]
    total_cents: int


# --- FastAPI App ---
app = FastAPI()


def validate_product_data(data: Dict[str, Any]) -> None:
    """Validate product data for negative values."""
    if "price_cents" in data and data["price_cents"] < 0:
        raise HTTPException(status_code=422, detail="price_cents cannot be negative")
    if "stock" in data and data["stock"] < 0:
        raise HTTPException(status_code=422, detail="stock cannot be negative")


# --- Products Endpoints ---
@app.post("/products", status_code=201)
def create_product(product: ProductCreate) -> ProductResponse:
    """Create a new product."""
    if product.price_cents < 0 or product.stock < 0:
        raise HTTPException(status_code=422, detail="price_cents and stock must be non-negative")

    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO Product (name, sku, price_cents, stock, category)
                VALUES (?, ?, ?, ?, ?)
                """,
                (product.name, product.sku, product.price_cents, product.stock, product.category),
            )
            conn.commit()
            product_id = cursor.lastrowid

            cursor.execute("SELECT * FROM Product WHERE id = ?", (product_id,))
            row = cursor.fetchone()
            return ProductResponse(**dict(row))
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="SKU already exists")


@app.get("/products")
def list_products(
    category: Optional[str] = None,
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
) -> List[ProductResponse]:
    """List products with optional filtering and pagination."""
    with get_db() as conn:
        cursor = conn.cursor()

        if category:
            cursor.execute(
                "SELECT * FROM Product WHERE category = ? LIMIT ? OFFSET ?",
                (category, limit, offset),
            )
        else:
            cursor.execute("SELECT * FROM Product LIMIT ? OFFSET ?", (limit, offset))

        rows = cursor.fetchall()
        return [ProductResponse(**dict(row)) for row in rows]


@app.get("/products/{product_id}")
def get_product(product_id: int) -> ProductResponse:
    """Get a product by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Product WHERE id = ?", (product_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Product not found")

        return ProductResponse(**dict(row))


@app.patch("/products/{product_id}")
def update_product(product_id: int, update: ProductUpdate) -> ProductResponse:
    """Update a product partially."""
    # Validate non-negative values
    data = update.model_dump(exclude_unset=True)
    validate_product_data(data)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Product WHERE id = ?", (product_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Product not found")

        # Build update query
        current = dict(row)
        for key, value in data.items():
            if value is not None:
                current[key] = value

        cursor.execute(
            """
            UPDATE Product SET name = ?, price_cents = ?, stock = ?, category = ?
            WHERE id = ?
            """,
            (current["name"], current["price_cents"], current["stock"], current["category"], product_id),
        )
        conn.commit()

        cursor.execute("SELECT * FROM Product WHERE id = ?", (product_id,))
        updated_row = cursor.fetchone()
        return ProductResponse(**dict(updated_row))


@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int) -> None:
    """Delete a product."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if product exists
        cursor.execute("SELECT * FROM Product WHERE id = ?", (product_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Product not found")

        # Check if product is referenced in any order
        cursor.execute("SELECT COUNT(*) FROM OrderItem WHERE product_id = ?", (product_id,))
        count = cursor.fetchone()[0]

        if count > 0:
            raise HTTPException(status_code=409, detail="Product is referenced in orders")

        cursor.execute("DELETE FROM Product WHERE id = ?", (product_id,))
        conn.commit()


# --- Orders Endpoints ---
@app.post("/orders", status_code=201)
def create_order(order: OrderCreate) -> OrderResponse:
    """Create a new order."""
    if not order.items:
        raise HTTPException(status_code=422, detail="items cannot be empty")

    for item in order.items:
        if item.quantity <= 0:
            raise HTTPException(status_code=422, detail="quantity must be positive")

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify all products exist and collect prices
        product_prices: Dict[int, int] = {}
        for item in order.items:
            cursor.execute("SELECT price_cents, stock FROM Product WHERE id = ?", (item.product_id,))
            row = cursor.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

            price, stock = row
            product_prices[item.product_id] = price

            # Check stock availability (before any update)
            if stock < item.quantity:
                raise HTTPException(status_code=409, detail="Insufficient stock")

        # All checks passed, create order and update stock (atomic)
        cursor.execute(
            'INSERT INTO "Order" (status, created_at) VALUES (?, ?)',
            ("pending", datetime.utcnow().isoformat()),
        )
        order_id = cursor.lastrowid

        # Insert order items and update stock
        total_cents = 0
        for item in order.items:
            unit_price = product_prices[item.product_id]
            cursor.execute(
                """
                INSERT INTO OrderItem (order_id, product_id, quantity, unit_price_cents)
                VALUES (?, ?, ?, ?)
                """,
                (order_id, item.product_id, item.quantity, unit_price),
            )

            # Decrease stock
            cursor.execute(
                "UPDATE Product SET stock = stock - ? WHERE id = ?",
                (item.quantity, item.product_id),
            )

            total_cents += unit_price * item.quantity

        conn.commit()

        # Fetch created order
        cursor.execute('SELECT * FROM "Order" WHERE id = ?', (order_id,))
        order_row = cursor.fetchone()

        cursor.execute("SELECT product_id, quantity, unit_price_cents FROM OrderItem WHERE order_id = ?", (order_id,))
        item_rows = cursor.fetchall()

        items = [OrderItemResponse(**dict(row)) for row in item_rows]

        return OrderResponse(
            id=order_id,
            status=order_row["status"],
            created_at=order_row["created_at"],
            items=items,
            total_cents=total_cents,
        )


@app.get("/orders/{order_id}")
def get_order(order_id: int) -> OrderResponse:
    """Get an order by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM "Order" WHERE id = ?', (order_id,))
        order_row = cursor.fetchone()

        if not order_row:
            raise HTTPException(status_code=404, detail="Order not found")

        cursor.execute("SELECT product_id, quantity, unit_price_cents FROM OrderItem WHERE order_id = ?", (order_id,))
        item_rows = cursor.fetchall()

        items = [OrderItemResponse(**dict(row)) for row in item_rows]
        total_cents = sum(item.quantity * item.unit_price_cents for item in items)

        return OrderResponse(
            id=order_row["id"],
            status=order_row["status"],
            created_at=order_row["created_at"],
            items=items,
            total_cents=total_cents,
        )


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int) -> OrderResponse:
    """Cancel an order."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM "Order" WHERE id = ?', (order_id,))
        order_row = cursor.fetchone()

        if not order_row:
            raise HTTPException(status_code=404, detail="Order not found")

        if order_row["status"] == "cancelled":
            raise HTTPException(status_code=409, detail="Order is already cancelled")

        # Restore stock
        cursor.execute("SELECT product_id, quantity FROM OrderItem WHERE order_id = ?", (order_id,))
        item_rows = cursor.fetchall()

        for row in item_rows:
            cursor.execute(
                "UPDATE Product SET stock = stock + ? WHERE id = ?",
                (row["quantity"], row["product_id"]),
            )

        # Update order status
        cursor.execute('UPDATE "Order" SET status = ? WHERE id = ?', ("cancelled", order_id))
        conn.commit()

        # Fetch updated order
        cursor.execute('SELECT * FROM "Order" WHERE id = ?', (order_id,))
        updated_order_row = cursor.fetchone()

        cursor.execute("SELECT product_id, quantity, unit_price_cents FROM OrderItem WHERE order_id = ?", (order_id,))
        item_rows = cursor.fetchall()

        items = [OrderItemResponse(**dict(row)) for row in item_rows]
        total_cents = sum(item.quantity * item.unit_price_cents for item in items)

        return OrderResponse(
            id=updated_order_row["id"],
            status=updated_order_row["status"],
            created_at=updated_order_row["created_at"],
            items=items,
            total_cents=total_cents,
        )


# --- Reports Endpoints ---
@app.get("/reports/low-stock")
def low_stock_report(threshold: int = Query(10, ge=0)) -> List[ProductResponse]:
    """Get products with stock below or equal to threshold."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Product WHERE stock <= ?", (threshold,))
        rows = cursor.fetchall()
        return [ProductResponse(**dict(row)) for row in rows]


@app.get("/reports/revenue-by-category")
def revenue_by_category() -> Dict[str, int]:
    """Get revenue by category (excluding cancelled orders)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.category, SUM(oi.quantity * oi.unit_price_cents) as total
            FROM OrderItem oi
            JOIN Product p ON oi.product_id = p.id
            JOIN "Order" o ON oi.order_id = o.id
            WHERE o.status != 'cancelled'
            GROUP BY p.category
        """)
        rows = cursor.fetchall()
        return {row["category"]: row["total"] or 0 for row in rows}


# Initialize database on startup
@app.on_event("startup")
def startup():
    init_db()
