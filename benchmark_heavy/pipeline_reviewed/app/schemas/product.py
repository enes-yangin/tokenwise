"""Product pydantic şemaları."""
from typing import Optional

from pydantic import BaseModel, Field


class ProductIn(BaseModel):
    name: str = Field(min_length=1)
    sku: str = Field(min_length=1)
    price_cents: int = Field(ge=0)
    stock: int = Field(ge=0)
    category: str = Field(min_length=1)


class ProductPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    sku: Optional[str] = Field(default=None, min_length=1)
    price_cents: Optional[int] = Field(default=None, ge=0)
    stock: Optional[int] = Field(default=None, ge=0)
    category: Optional[str] = Field(default=None, min_length=1)
