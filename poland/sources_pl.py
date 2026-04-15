from __future__ import annotations

import os
import random
import re
import time
import logging
from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)


def _bool_env(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _headers() -> Dict[str, str]:
    try:
        ua = UserAgent().random
    except Exception:
        ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    return {"User-Agent": ua}


def _delay() -> None:
    time.sleep(random.uniform(1, 3))


def _parse_price(value: str) -> Optional[float]:
    if not value:
        return None
    cleaned = re.sub(r"[^\d,\.]", "", value)
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def allegro_device_flow_instructions() -> str:
    return (
        "Register at https://developer.allegro.pl/, create an app, set ALLEGRO_CLIENT_ID and "
        "ALLEGRO_CLIENT_SECRET, then complete OAuth2 device flow to obtain token. "
        "Optionally set ALLEGRO_ACCESS_TOKEN for scaffolded API requests."
    )


def allegro_search_scaffold(ean: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    if not _bool_env("ENABLE_ALLEGRO", True):
        return None

    token = os.getenv("ALLEGRO_ACCESS_TOKEN")
    if not token:
        return None

    _delay()
    try:
        response = requests.get(
            "https://api.allegro.pl/offers/listing",
            params={"phrase": ean},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.allegro.public.v1+json",
                **_headers(),
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Allegro scaffold request failed for EAN %s: %s", ean, exc)
        return None

    items = ((payload.get("items") or {}).get("regular") or [])
    if not items:
        return None

    first = items[0]
    price_block = ((first.get("sellingMode") or {}).get("price") or {})

    return {
        "ean": ean,
        "product_name": first.get("name"),
        "brand": None,
        "category": None,
        "price": float(price_block["amount"]) if price_block.get("amount") else None,
        "currency": price_block.get("currency") or "PLN",
        "source": "allegro",
    }


def scrape_ceneo(ean: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    if not _bool_env("ENABLE_CENEO", True):
        return None

    _delay()
    try:
        response = requests.get(
            f"https://www.ceneo.pl/;szukaj-{ean}",
            headers=_headers(),
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Ceneo request failed for EAN %s: %s", ean, exc)
        return None

    soup = BeautifulSoup(response.text, "lxml")
    name_el = soup.select_one(".cat-prod-row-name") or soup.select_one("h1")
    price_el = soup.select_one(".price") or soup.select_one(".product-price")

    if not name_el and not price_el:
        return None

    return {
        "ean": ean,
        "product_name": name_el.get_text(" ", strip=True) if name_el else None,
        "brand": None,
        "category": None,
        "price": _parse_price(price_el.get_text(" ", strip=True)) if price_el else None,
        "currency": "PLN",
        "source": "ceneo",
    }
