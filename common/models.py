from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Offer:
    product_name: str
    source: str
    link: str
    item_price: Optional[float]
    currency: Optional[str]
    delivery_cost: Optional[float]
