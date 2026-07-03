"""Order pydantic şemaları."""
from typing import List

from pydantic import BaseModel, Field


class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderIn(BaseModel):
    items: List[OrderItemIn] = Field(min_length=1)
