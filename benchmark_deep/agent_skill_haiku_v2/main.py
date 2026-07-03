import os
import sqlite3
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, field_validator

# ===== DATABASE SETUP =====

DATABASE_URL = os.getenv("DATABASE_URL", "inventory.db")
_db_connection = None


def get_db_connection():
    """Get or create database connection (singleton for :memory:)."""
    global _db_connection
    if DATABASE_URL == ":memory:":
        if _db_connection is None:
            _db_connection = sqlite3.connect(":memory:", check_same_thread=False)
        return _db_connection
    else:
        return sqlite3.connect(DATABASE_URL)


@contextmanager
def get_db():
    """Context manager for database connection."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        if DATABASE_URL != ":memory:":
            conn.close()


def init_db():
    """Initialize database schema."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sku TEXT NOT NULL UNIQUE,
                price_cents INTEGER NOT NULL,
                stock INTEGER NOT NULL,
                category TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price_cents INTEGER NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        """)
        conn.commit()


# ===== PYDANTIC MODELS =====

class ProductCreate(BaseModel):
    name: str
    sku: str
    price_cents: int
    stock: int
    category: str

    @field_validator("price_cents", "stock")
    def check_non_negative(cls, v):
        if v < 0:
            raise ValueError("must be non-negative")
        return v


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    price_cents: Optional[int] = None
    stock: Optional[int] = None
    category: Optional[str] = None

    @field_validator("price_cents", "stock")
    def check_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("must be non-negative")
        return v


class Product(BaseModel):
    id: int
    name: str
    sku: str
    price_cents: int
    stock: int
    category: str


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int

    @field_validator("quantity")
    def check_quantity(cls, v):
        if v <= 0:
            raise ValueError("must be positive")
        return v


class OrderCreate(BaseModel):
    items: List[OrderItemCreate]

    @field_validator("items")
    def check_non_empty(cls, v):
        if not v:
            raise ValueError("must have at least one item")
        return v


class OrderItem(BaseModel):
    product_id: int
    quantity: int
    unit_price_cents: int


class Order(BaseModel):
    id: int
    status: str
    created_at: str
    items: List[OrderItem]
    total_cents: int


# ===== FASTAPI APP =====

app = FastAPI()


# Initialize DB on startup
init_db()


# ===== PRODUCT ENDPOINTS =====

@app.post("/products", status_code=201)
def create_product(product: ProductCreate) -> Product:
    """Create a new product."""
    with get_db() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO products (name, sku, price_cents, stock, category) VALUES (?, ?, ?, ?, ?)",
                (product.name, product.sku, product.price_cents, product.stock, product.category),
            )
            conn.commit()
            product_id = cursor.lastrowid
            return get_product_by_id(product_id)
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise HTTPException(status_code=409, detail="SKU already exists")
            raise


@app.get("/products")
def list_products(
    category: Optional[str] = None,
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
) -> List[Product]:
    """List products with optional filtering and pagination."""
    with get_db() as conn:
        query = "SELECT * FROM products"
        params = []

        if category:
            query += " WHERE category = ?"
            params.append(category)

        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [row_to_product(row) for row in rows]


@app.get("/products/{product_id}")
def get_product(product_id: int) -> Product:
    """Get a product by ID."""
    product = get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def get_product_by_id(product_id: int) -> Optional[Product]:
    """Helper: get product by ID from DB."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return row_to_product(row) if row else None


def row_to_product(row) -> Product:
    """Convert DB row to Product model."""
    return Product(
        id=row["id"],
        name=row["name"],
        sku=row["sku"],
        price_cents=row["price_cents"],
        stock=row["stock"],
        category=row["category"],
    )


@app.patch("/products/{product_id}")
def update_product(product_id: int, update: ProductUpdate) -> Product:
    """Update product fields."""
    with get_db() as conn:
        # Check product exists
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Build update query
        updates = {}
        if update.name is not None:
            updates["name"] = update.name
        if update.sku is not None:
            updates["sku"] = update.sku
        if update.price_cents is not None:
            updates["price_cents"] = update.price_cents
        if update.stock is not None:
            updates["stock"] = update.stock
        if update.category is not None:
            updates["category"] = update.category

        if not updates:
            return row_to_product(product)

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        query = f"UPDATE products SET {set_clause} WHERE id = ?"
        params = list(updates.values()) + [product_id]

        try:
            conn.execute(query, params)
            conn.commit()
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise HTTPException(status_code=409, detail="SKU already exists")
            raise

        return get_product_by_id(product_id)


@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int):
    """Delete a product."""
    with get_db() as conn:
        # Check product exists
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Check if product is referenced in any order
        order_item = conn.execute(
            "SELECT * FROM order_items WHERE product_id = ?", (product_id,)
        ).fetchone()
        if order_item:
            raise HTTPException(status_code=409, detail="Product is referenced in an order")

        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()


# ===== ORDER ENDPOINTS =====

@app.post("/orders", status_code=201)
def create_order(order_data: OrderCreate) -> Order:
    """Create a new order with items."""
    with get_db() as conn:
        # Validate all products exist
        for item in order_data.items:
            product = conn.execute(
                "SELECT * FROM products WHERE id = ?", (item.product_id,)
            ).fetchone()
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        # Check all items have sufficient stock (atomic check)
        for item in order_data.items:
            product = conn.execute(
                "SELECT stock FROM products WHERE id = ?", (item.product_id,)
            ).fetchone()
            if product["stock"] < item.quantity:
                raise HTTPException(status_code=409, detail="Insufficient stock")

        # Create order
        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        cursor = conn.execute(
            "INSERT INTO orders (status, created_at) VALUES (?, ?)",
            ("pending", created_at),
        )
        conn.commit()
        order_id = cursor.lastrowid

        # Add items and reduce stock
        for item in order_data.items:
            product = conn.execute(
                "SELECT price_cents FROM products WHERE id = ?", (item.product_id,)
            ).fetchone()
            unit_price = product["price_cents"]

            conn.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents) VALUES (?, ?, ?, ?)",
                (order_id, item.product_id, item.quantity, unit_price),
            )

            conn.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (item.quantity, item.product_id),
            )

        conn.commit()
        return get_order_by_id(order_id)


@app.get("/orders/{order_id}")
def get_order(order_id: int) -> Order:
    """Get an order by ID with items and total."""
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def get_order_by_id(order_id: int) -> Optional[Order]:
    """Helper: get order by ID from DB."""
    with get_db() as conn:
        order_row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order_row:
            return None

        items_rows = conn.execute(
            "SELECT product_id, quantity, unit_price_cents FROM order_items WHERE order_id = ?",
            (order_id,),
        ).fetchall()

        items = [
            OrderItem(
                product_id=row["product_id"],
                quantity=row["quantity"],
                unit_price_cents=row["unit_price_cents"],
            )
            for row in items_rows
        ]

        total_cents = sum(item.quantity * item.unit_price_cents for item in items)

        return Order(
            id=order_row["id"],
            status=order_row["status"],
            created_at=order_row["created_at"],
            items=items,
            total_cents=total_cents,
        )


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int) -> Order:
    """Cancel an order and restore stock."""
    with get_db() as conn:
        # Check order exists
        order_row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order_row:
            raise HTTPException(status_code=404, detail="Order not found")

        # Check if already cancelled
        if order_row["status"] == "cancelled":
            raise HTTPException(status_code=409, detail="Order already cancelled")

        # Get order items
        items_rows = conn.execute(
            "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
            (order_id,),
        ).fetchall()

        # Update order status
        conn.execute("UPDATE orders SET status = ? WHERE id = ?", ("cancelled", order_id))

        # Restore stock
        for row in items_rows:
            conn.execute(
                "UPDATE products SET stock = stock + ? WHERE id = ?",
                (row["quantity"], row["product_id"]),
            )

        conn.commit()
        return get_order_by_id(order_id)


# ===== REPORT ENDPOINTS =====

@app.get("/reports/low-stock")
def report_low_stock(threshold: int = Query(10, ge=0)) -> List[Product]:
    """Get products with stock <= threshold."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM products WHERE stock <= ? ORDER BY stock ASC", (threshold,)
        ).fetchall()
        return [row_to_product(row) for row in rows]


@app.get("/reports/revenue-by-category")
def report_revenue_by_category() -> Dict[str, int]:
    """Get revenue by category from non-cancelled orders."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT p.category, SUM(oi.quantity * oi.unit_price_cents) as revenue
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.status != 'cancelled'
            GROUP BY p.category
            """,
        ).fetchall()

        return {row["category"]: row["revenue"] for row in rows}
