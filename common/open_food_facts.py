from __future__ import annotations

from typing import Any, Dict, Optional

import requests


class OpenFoodFactsClient:
    BASE_URL = "https://world.openfoodfacts.org/api/v2/product"

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
        if payload.get("status") != 1:
            return None
        product = payload.get("product") or {}
        if not product:
            return None

        return {
            "ean": ean,
            "product_name": product.get("product_name") or product.get("generic_name"),
            "brand": (product.get("brands") or "").split(",")[0].strip() or None,
            "category": (product.get("categories_tags") or [None])[0],
            "price": None,
            "currency": None,
            "source": "open_food_facts",
        }
