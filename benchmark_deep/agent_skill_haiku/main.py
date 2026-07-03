import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional, List
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, validator


app = FastAPI()


@contextmanager
def get_db():
    """Get DB connection."""
    db_path = os.environ.get('DATABASE_URL', 'inventory.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Initialize tables
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sku TEXT UNIQUE NOT NULL,
        price_cents INTEGER NOT NULL,
        stock INTEGER NOT NULL,
        category TEXT NOT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS order_items (
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price_cents INTEGER NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )''')
    conn.commit()

    try:
        yield conn
    finally:
        conn.close()


# Models
class ProductRequest(BaseModel):
    name: str
    sku: str
    price_cents: int
    stock: int
    category: str

    @validator('price_cents', 'stock')
    def must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('must be non-negative')
        return v


class ProductResponse(BaseModel):
    id: int
    name: str
    sku: str
    price_cents: int
    stock: int
    category: str


class ProductPatchRequest(BaseModel):
    name: Optional[str] = None
    price_cents: Optional[int] = None
    stock: Optional[int] = None
    category: Optional[str] = None

    @validator('price_cents', 'stock', pre=True, always=False)
    def validate_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError('must be non-negative')
        return v


class OrderItemRequest(BaseModel):
    product_id: int
    quantity: int

    @validator('quantity')
    def quantity_positive(cls, v):
        if v <= 0:
            raise ValueError('quantity must be > 0')
        return v


class OrderRequest(BaseModel):
    items: List[OrderItemRequest]

    @validator('items')
    def items_not_empty(cls, v):
        if not v:
            raise ValueError('items cannot be empty')
        return v


class OrderItemResponse(BaseModel):
    product_id: int
    quantity: int
    unit_price_cents: int


class OrderResponse(BaseModel):
    id: int
    status: str
    created_at: str
    items: List[OrderItemResponse]
    total_cents: int


# Endpoints
@app.post('/products', status_code=201)
def create_product(req: ProductRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''INSERT INTO products (name, sku, price_cents, stock, category)
                VALUES (?, ?, ?, ?, ?)''',
                (req.name, req.sku, req.price_cents, req.stock, req.category))
            conn.commit()
            product_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail='SKU already exists')

        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        row = cursor.fetchone()
        return {
            'id': row['id'],
            'name': row['name'],
            'sku': row['sku'],
            'price_cents': row['price_cents'],
            'stock': row['stock'],
            'category': row['category']
        }


@app.get('/products')
def list_products(
    category: Optional[str] = None,
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0)
):
    with get_db() as conn:
        cursor = conn.cursor()
        if category:
            cursor.execute('SELECT * FROM products WHERE category = ? LIMIT ? OFFSET ?',
                (category, limit, offset))
        else:
            cursor.execute('SELECT * FROM products LIMIT ? OFFSET ?', (limit, offset))
        rows = cursor.fetchall()

        return [{
            'id': row['id'],
            'name': row['name'],
            'sku': row['sku'],
            'price_cents': row['price_cents'],
            'stock': row['stock'],
            'category': row['category']
        } for row in rows]


@app.get('/products/{product_id}')
def get_product(product_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail='Product not found')

        return {
            'id': row['id'],
            'name': row['name'],
            'sku': row['sku'],
            'price_cents': row['price_cents'],
            'stock': row['stock'],
            'category': row['category']
        }


@app.patch('/products/{product_id}')
def patch_product(product_id: int, req: ProductPatchRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail='Product not found')

        updates = {}
        if req.name is not None:
            updates['name'] = req.name
        if req.price_cents is not None:
            updates['price_cents'] = req.price_cents
        if req.stock is not None:
            updates['stock'] = req.stock
        if req.category is not None:
            updates['category'] = req.category

        if updates:
            set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
            cursor.execute(f'UPDATE products SET {set_clause} WHERE id = ?',
                (*updates.values(), product_id))
            conn.commit()

        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        row = cursor.fetchone()
        return {
            'id': row['id'],
            'name': row['name'],
            'sku': row['sku'],
            'price_cents': row['price_cents'],
            'stock': row['stock'],
            'category': row['category']
        }


@app.delete('/products/{product_id}', status_code=204)
def delete_product(product_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail='Product not found')

        # Check referential integrity
        cursor.execute('SELECT COUNT(*) as cnt FROM order_items WHERE product_id = ?', (product_id,))
        if cursor.fetchone()['cnt'] > 0:
            raise HTTPException(status_code=409, detail='Product referenced in orders')

        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        return None


@app.post('/orders', status_code=201)
def create_order(req: OrderRequest):
    with get_db() as conn:
        cursor = conn.cursor()

        # Check products exist and stock
        products = {}
        for item in req.items:
            cursor.execute('SELECT * FROM products WHERE id = ?', (item.product_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Product not found')
            products[item.product_id] = row

        # Atomic check: all items have sufficient stock
        for item in req.items:
            if products[item.product_id]['stock'] < item.quantity:
                raise HTTPException(status_code=409, detail='Insufficient stock')

        # Create order
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute('INSERT INTO orders (status, created_at) VALUES (?, ?)',
            ('pending', now))
        order_id = cursor.lastrowid

        # Add items and deduct stock
        total_cents = 0
        for item in req.items:
            price = products[item.product_id]['price_cents']
            cursor.execute('''INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents)
                VALUES (?, ?, ?, ?)''',
                (order_id, item.product_id, item.quantity, price))

            cursor.execute('UPDATE products SET stock = stock - ? WHERE id = ?',
                (item.quantity, item.product_id))

            total_cents += price * item.quantity

        conn.commit()

        # Return order
        cursor.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,))
        items_rows = cursor.fetchall()

        return {
            'id': order_id,
            'status': 'pending',
            'created_at': now,
            'items': [
                {
                    'product_id': row['product_id'],
                    'quantity': row['quantity'],
                    'unit_price_cents': row['unit_price_cents']
                } for row in items_rows
            ],
            'total_cents': total_cents
        }


@app.get('/orders/{order_id}')
def get_order(order_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail='Order not found')

        cursor.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,))
        items_rows = cursor.fetchall()

        total_cents = sum(r['quantity'] * r['unit_price_cents'] for r in items_rows)

        return {
            'id': row['id'],
            'status': row['status'],
            'created_at': row['created_at'],
            'items': [
                {
                    'product_id': r['product_id'],
                    'quantity': r['quantity'],
                    'unit_price_cents': r['unit_price_cents']
                } for r in items_rows
            ],
            'total_cents': total_cents
        }


@app.post('/orders/{order_id}/cancel')
def cancel_order(order_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail='Order not found')

        if row['status'] == 'cancelled':
            raise HTTPException(status_code=409, detail='Order already cancelled')

        # Restore stock
        cursor.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,))
        items_rows = cursor.fetchall()
        for item_row in items_rows:
            cursor.execute('UPDATE products SET stock = stock + ? WHERE id = ?',
                (item_row['quantity'], item_row['product_id']))

        cursor.execute('UPDATE orders SET status = ? WHERE id = ?', ('cancelled', order_id))
        conn.commit()

        return {
            'id': row['id'],
            'status': 'cancelled',
            'created_at': row['created_at']
        }


@app.get('/reports/low-stock')
def low_stock_report(threshold: int = Query(10, ge=0)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE stock <= ? ORDER BY stock ASC', (threshold,))
        rows = cursor.fetchall()

        return [{
            'id': row['id'],
            'name': row['name'],
            'sku': row['sku'],
            'price_cents': row['price_cents'],
            'stock': row['stock'],
            'category': row['category']
        } for row in rows]


@app.get('/reports/revenue-by-category')
def revenue_by_category():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.category, SUM(oi.quantity * oi.unit_price_cents) as total_cents
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            JOIN products p ON oi.product_id = p.id
            WHERE o.status != ?
            GROUP BY p.category
        ''', ('cancelled',))
        rows = cursor.fetchall()

        return {row['category']: row['total_cents'] for row in rows}
