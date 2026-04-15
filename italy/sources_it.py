from __future__ import annotations

import os
import random
import re
import time
from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


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
    cleaned = cleaned.replace(".", "").replace(",", ".") if "," in cleaned else cleaned
    try:
        return float(cleaned)
    except ValueError:
        return None


def scrape_trovaprezzi(ean: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    if not _bool_env("ENABLE_TROVAPREZZI", True):
        return None

    _delay()
    try:
        response = requests.get(
            f"https://www.trovaprezzi.it/cerca.aspx?libera={ean}",
            headers=_headers(),
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException:
        return None

    soup = BeautifulSoup(response.text, "lxml")
    name_el = soup.select_one("h1") or soup.select_one(".product-name") or soup.select_one(".itemTitle")
    price_el = soup.select_one(".prezzo") or soup.select_one(".price") or soup.select_one(".itemPrice")

    if not name_el and not price_el:
        return None

    return {
        "ean": ean,
        "product_name": name_el.get_text(strip=True) if name_el else None,
        "brand": None,
        "category": None,
        "price": _parse_price(price_el.get_text(" ", strip=True)) if price_el else None,
        "currency": "EUR",
        "source": "trovaprezzi",
    }


def scrape_amazon_it_placeholder(ean: str) -> Optional[Dict[str, Any]]:
    if not _bool_env("ENABLE_AMAZON_IT", False):
        return None

    print(
        "Amazon.it scraping is disabled by default and may violate Terms of Service. "
        "Enable only after legal/ToS review and robots.txt checks."
    )
    return None
