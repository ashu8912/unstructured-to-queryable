from pydantic import BaseModel
from typing import Optional

class LineItem(BaseModel):
    description: str
    amount: float

class Receipt(BaseModel):
    store: Optional[str] = None
    date: Optional[str] = None        # ISO format: YYYY-MM-DD
    total: Optional[float] = None
    currency: Optional[str] = None
    items: list[LineItem] = []