import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, validator

# Database setup
DB_PATH = os.getenv("DB_PATH", "inventory.db")

def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database schema."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT UNIQUE NOT NULL,
            price_cents INTEGER NOT NULL,
            stock INTEGER NOT NULL,
            category TEXT NOT NULL
        )
    """)

    # Orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    """)

    # OrderItems table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price_cents INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    conn.commit()
    conn.close()

# Initialize on module load
init_db()

# Pydantic models
class ProductCreate(BaseModel):
    name: str
    sku: str
    price_cents: int
    stock: int
    category: str

    @validator('price_cents', 'stock')
    def must_not_be_negative(cls, v):
        if v < 0:
            raise ValueError("must be >= 0")
        return v

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    price_cents: Optional[int] = None
    stock: Optional[int] = None
    category: Optional[str] = None

    @validator('price_cents', 'stock', pre=True, always=True)
    def must_not_be_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("must be >= 0")
        return v

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

    @validator('quantity')
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("quantity must be > 0")
        return v

class OrderItemResponse(BaseModel):
    product_id: int
    quantity: int
    unit_price_cents: int

class OrderCreate(BaseModel):
    items: List[OrderItemCreate]

    @validator('items')
    def items_must_not_be_empty(cls, v):
        if not v:
            raise ValueError("items must not be empty")
        return v

class OrderResponse(BaseModel):
    id: int
    status: str
    created_at: str
    items: List[OrderItemResponse]
    total_cents: int

# FastAPI app
app = FastAPI()

# Helper functions
def product_row_to_dict(row) -> ProductResponse:
    """Convert a database row to ProductResponse."""
    return ProductResponse(
        id=row['id'],
        name=row['name'],
        sku=row['sku'],
        price_cents=row['price_cents'],
        stock=row['stock'],
        category=row['category']
    )

def get_order_with_items(order_id: int) -> Optional[Dict[str, Any]]:
    """Fetch an order with all its items."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, status, created_at FROM orders WHERE id = ?", (order_id,))
    order_row = cursor.fetchone()

    if not order_row:
        conn.close()
        return None

    cursor.execute("""
        SELECT product_id, quantity, unit_price_cents FROM order_items WHERE order_id = ?
    """, (order_id,))
    items_rows = cursor.fetchall()

    conn.close()

    total_cents = sum(item['quantity'] * item['unit_price_cents'] for item in items_rows)

    return {
        'id': order_row['id'],
        'status': order_row['status'],
        'created_at': order_row['created_at'],
        'items': [
            OrderItemResponse(
                product_id=item['product_id'],
                quantity=item['quantity'],
                unit_price_cents=item['unit_price_cents']
            ) for item in items_rows
        ],
        'total_cents': total_cents
    }

# Products endpoints
@app.post("/products", status_code=201)
def create_product(product: ProductCreate):
    """Create a new product."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO products (name, sku, price_cents, stock, category)
            VALUES (?, ?, ?, ?, ?)
        """, (product.name, product.sku, product.price_cents, product.stock, product.category))
        conn.commit()
        product_id = cursor.lastrowid

        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        conn.close()

        return product_row_to_dict(row)
    except sqlite3.IntegrityError as e:
        conn.close()
        if "UNIQUE constraint failed: products.sku" in str(e):
            raise HTTPException(status_code=409, detail="SKU already exists")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/products")
def list_products(
    category: Optional[str] = None,
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0)
):
    """List products with optional filtering and pagination."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if category:
        cursor.execute("""
            SELECT * FROM products WHERE category = ? LIMIT ? OFFSET ?
        """, (category, limit, offset))
    else:
        cursor.execute("""
            SELECT * FROM products LIMIT ? OFFSET ?
        """, (limit, offset))

    rows = cursor.fetchall()
    conn.close()

    return [product_row_to_dict(row) for row in rows]

@app.get("/products/{product_id}")
def get_product(product_id: int):
    """Get a specific product by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    return product_row_to_dict(row)

@app.patch("/products/{product_id}")
def update_product(product_id: int, update: ProductUpdate):
    """Partially update a product."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")

    # Build update query
    updates = {}
    if update.name is not None:
        updates['name'] = update.name
    if update.sku is not None:
        updates['sku'] = update.sku
    if update.price_cents is not None:
        updates['price_cents'] = update.price_cents
    if update.stock is not None:
        updates['stock'] = update.stock
    if update.category is not None:
        updates['category'] = update.category

    if updates:
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [product_id]

        try:
            cursor.execute(f"UPDATE products SET {set_clause} WHERE id = ?", values)
            conn.commit()
        except sqlite3.IntegrityError as e:
            conn.close()
            if "UNIQUE constraint failed: products.sku" in str(e):
                raise HTTPException(status_code=409, detail="SKU already exists")
            raise HTTPException(status_code=400, detail=str(e))

    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()

    return product_row_to_dict(row)

@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int):
    """Delete a product."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if product is referenced in any order
    cursor.execute("SELECT COUNT(*) as count FROM order_items WHERE product_id = ?", (product_id,))
    if cursor.fetchone()['count'] > 0:
        conn.close()
        raise HTTPException(status_code=409, detail="Product is referenced in existing orders")

    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

# Orders endpoints
@app.post("/orders", status_code=201)
def create_order(order: OrderCreate):
    """Create a new order."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verify all products exist and have sufficient stock
        product_quantities = {}
        for item in order.items:
            cursor.execute("SELECT id, price_cents, stock FROM products WHERE id = ?", (item.product_id,))
            product = cursor.fetchone()

            if not product:
                conn.close()
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

            product_quantities[item.product_id] = {
                'quantity': item.quantity,
                'price_cents': product['price_cents'],
                'current_stock': product['stock']
            }

        # Check all stock availability before making any changes (atomic check)
        for product_id, info in product_quantities.items():
            if info['current_stock'] < info['quantity']:
                conn.close()
                raise HTTPException(status_code=409, detail=f"Insufficient stock for product {product_id}")

        # Create order
        created_at = datetime.utcnow().isoformat() + "Z"
        cursor.execute("""
            INSERT INTO orders (status, created_at)
            VALUES (?, ?)
        """, ("pending", created_at))
        order_id = cursor.lastrowid

        # Add order items and update stock
        total_cents = 0
        for item in order.items:
            unit_price = product_quantities[item.product_id]['price_cents']
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents)
                VALUES (?, ?, ?, ?)
            """, (order_id, item.product_id, item.quantity, unit_price))

            cursor.execute("""
                UPDATE products SET stock = stock - ? WHERE id = ?
            """, (item.quantity, item.product_id))

            total_cents += item.quantity * unit_price

        conn.commit()
        conn.close()

        # Fetch and return the created order
        order_data = get_order_with_items(order_id)
        return OrderResponse(**order_data)

    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/orders/{order_id}")
def get_order(order_id: int):
    """Get a specific order by ID."""
    order_data = get_order_with_items(order_id)

    if not order_data:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderResponse(**order_data)

@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int):
    """Cancel an order and restore stock."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
    order_row = cursor.fetchone()

    if not order_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    if order_row['status'] == 'cancelled':
        conn.close()
        raise HTTPException(status_code=409, detail="Order is already cancelled")

    # Get order items
    cursor.execute("""
        SELECT product_id, quantity FROM order_items WHERE order_id = ?
    """, (order_id,))
    items = cursor.fetchall()

    # Restore stock
    for item in items:
        cursor.execute("""
            UPDATE products SET stock = stock + ? WHERE id = ?
        """, (item['quantity'], item['product_id']))

    # Update order status
    cursor.execute("""
        UPDATE orders SET status = ? WHERE id = ?
    """, ('cancelled', order_id))

    conn.commit()
    conn.close()

    # Return updated order
    order_data = get_order_with_items(order_id)
    return OrderResponse(**order_data)

# Reports endpoints
@app.get("/reports/low-stock")
def get_low_stock(threshold: int = Query(10, ge=0)):
    """Get products with stock at or below threshold."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM products WHERE stock <= ? ORDER BY id
    """, (threshold,))
    rows = cursor.fetchall()
    conn.close()

    return [product_row_to_dict(row) for row in rows]

@app.get("/reports/revenue-by-category")
def get_revenue_by_category():
    """Get revenue by category for non-cancelled orders."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.category,
            SUM(oi.quantity * oi.unit_price_cents) as total_cents
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        JOIN products p ON p.id = oi.product_id
        WHERE o.status != 'cancelled'
        GROUP BY p.category
    """)
    rows = cursor.fetchall()
    conn.close()

    result = {}
    for row in rows:
        result[row['category']] = row['total_cents'] if row['total_cents'] is not None else 0

    return result
