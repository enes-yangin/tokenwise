"""Order pydantic şemaları."""
from typing import List

from pydantic import BaseModel, Field


class OrderItemIn(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    items: List[OrderItemIn] = Field(min_length=1)


class OrderItem(BaseModel):
    product_id: int
    quantity: int
    unit_price_cents: int


class OrderResponse(BaseModel):
    id: int
    status: str
    created_at: str
    items: List[OrderItem]
    total_cents: int
