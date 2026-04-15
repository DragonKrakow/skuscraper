from __future__ import annotations

from typing import Any, Dict, Optional

import requests


class OpenProductDataClient:
    BASE_URL = "https://world.openproductdata.org/api/v3/product"

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout

    def fetch(self, ean: str) -> Optional[Dict[str, Any]]:
        try:
            response = requests.get(
                f"{self.BASE_URL}/{ean}.json",
                timeout=self.timeout,
            )
            response.raise_for_status()
            return self.parse_product(response.json(), ean)
        except (requests.RequestException, ValueError, KeyError, TypeError):
            return None

    @staticmethod
    def parse_product(payload: Dict[str, Any], ean: str) -> Optional[Dict[str, Any]]:
        product = payload.get("product") or payload.get("data") or {}
        if not product:
            return None

        brand_value = product.get("brand") or product.get("brands")
        if isinstance(brand_value, list):
            brand_value = brand_value[0] if brand_value else None

        return {
            "ean": ean,
            "product_name": product.get("name") or product.get("product_name"),
            "brand": brand_value,
            "category": product.get("category") or product.get("categories"),
            "price": product.get("price"),
            "currency": product.get("currency"),
            "source": "open_product_data",
        }
