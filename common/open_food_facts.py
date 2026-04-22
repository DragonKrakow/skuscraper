from __future__ import annotations

import re
from typing import Any, Dict, Optional

import requests


class OpenFoodFactsClient:
    BASE_URL = "https://world.openfoodfacts.org/api/v2/product"
    SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
    EAN_PATTERN = re.compile(r"^(?:\d{8}|\d{13})$")

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

    def search(self, query: str, page_size: int = 20) -> list[Dict[str, Any]]:
        try:
            response = requests.get(
                self.SEARCH_URL,
                params={
                    "search_terms": query,
                    "search_simple": 1,
                    "action": "process",
                    "json": 1,
                    "page_size": page_size,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError, TypeError):
            return []

        products = payload.get("products") or []
        matches: list[Dict[str, Any]] = []
        for product in products:
            code = str(product.get("code") or "").strip()
            if not self.EAN_PATTERN.match(code):
                continue
            matches.append(
                {
                    "ean": code,
                    "product_name": product.get("product_name") or product.get("generic_name"),
                    "brand": (product.get("brands") or "").split(",")[0].strip() or None,
                    "category": (product.get("categories_tags") or [None])[0],
                    "source": "open_food_facts",
                }
            )
        return matches

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
