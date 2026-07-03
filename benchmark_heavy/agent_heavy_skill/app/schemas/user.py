"""User pydantic şemaları."""
from typing import Optional

from pydantic import BaseModel, Field


class UserIn(BaseModel):
    email: str = Field(min_length=3)
    name: str = Field(min_length=1)


class UserPatch(BaseModel):
    email: Optional[str] = Field(default=None, min_length=3)
    name: Optional[str] = Field(default=None, min_length=1)
