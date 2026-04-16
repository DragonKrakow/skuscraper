from __future__ import annotations

import logging
import os
import random
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import quote_plus, urljoin, urlparse
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)


def _bool_env(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _parse_price(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    cleaned = re.sub(r"[^\d,\.]", "", value)
    if not cleaned:
        return None
    cleaned = cleaned.replace(".", "").replace(",", ".") if "," in cleaned else cleaned
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_rating(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    match = re.search(r"(\d+(?:[.,]\d+)?)", value)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def _headers() -> Dict[str, str]:
    try:
        ua = UserAgent().random
    except Exception:
        ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    return {"User-Agent": ua}


@dataclass
class SourceConfig:
    enabled: bool
    timeout: int = 12
    retries: int = 2
    backoff_seconds: float = 1.0
    rate_limit_seconds: float = 1.0
    proxy: Optional[str] = None


class KeywordSearchSource:
    source_name = "unknown"

    def __init__(self, config: SourceConfig) -> None:
        self.config = config
        self._last_request_at = 0.0

    def _wait_for_rate_limit(self) -> None:
        if self._last_request_at <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        wait_seconds = max(0.0, self.config.rate_limit_seconds - elapsed)
        if wait_seconds:
            time.sleep(wait_seconds)

    def _request_text(self, url: str) -> Optional[str]:
        if not self.config.enabled:
            return None

        proxies = {"http": self.config.proxy, "https": self.config.proxy} if self.config.proxy else None
        attempts = max(1, self.config.retries + 1)
        for attempt in range(attempts):
            self._wait_for_rate_limit()
            try:
                response = requests.get(
                    url,
                    headers=_headers(),
                    timeout=self.config.timeout,
                    proxies=proxies,
                )
                self._last_request_at = time.monotonic()
                response.raise_for_status()
                return response.text
            except requests.RequestException as exc:
                if attempt == attempts - 1:
                    logger.warning("%s request failed (%s): %s", self.source_name, url, exc)
                    return None
                delay = self.config.backoff_seconds * (2 ** (attempt + 1)) + random.uniform(0.0, 0.2)
                time.sleep(delay)
        return None

    def search(
        self,
        query: Optional[str] = None,
        search_url: Optional[str] = None,
        sort_by: str = "best_match",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError


def parse_amazon_it_search_html(html: str, page_url: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    results: List[Dict[str, Any]] = []

    for item in soup.select("div.s-result-item[data-component-type='s-search-result']"):
        asin = (item.get("data-asin") or "").strip() or None
        title_el = item.select_one("h2 a span")
        link_el = item.select_one("h2 a")
        if not title_el or not link_el:
            continue

        price_text = None
        whole = item.select_one("span.a-price-whole")
        frac = item.select_one("span.a-price-fraction")
        if whole:
            price_text = f"{whole.get_text(strip=True)}{',' + frac.get_text(strip=True) if frac else ''}"
        if not price_text:
            offscreen = item.select_one("span.a-offscreen")
            price_text = offscreen.get_text(" ", strip=True) if offscreen else None

        rating_text = None
        rating_el = item.select_one("span.a-icon-alt")
        if rating_el:
            rating_text = rating_el.get_text(" ", strip=True)

        results.append(
            {
                "title": title_el.get_text(" ", strip=True),
                "asin": asin,
                "url": urljoin(page_url, link_el.get("href") or ""),
                "price": _parse_price(price_text),
                "currency": "EUR" if price_text else None,
                "image": (item.select_one("img.s-image") or {}).get("src"),
                "seller": None,
                "brand": None,
                "rating": _parse_rating(rating_text),
                "source": "amazon_it",
            }
        )

    return results


def parse_ebay_it_rss(xml_payload: str) -> List[Dict[str, Any]]:
    try:
        root = ElementTree.fromstring(xml_payload)
    except ElementTree.ParseError:
        return []

    results: List[Dict[str, Any]] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = item.findtext("description") or ""
        price_match = re.search(r"(?:EUR\s*|€\s*)(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*EUR", description, re.I)
        raw_price = next((group for group in price_match.groups() if group), None) if price_match else None
        item_id_match = re.search(r"/(\d{9,})", link)
        image_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', description, re.I)

        if not title or not link:
            continue

        results.append(
            {
                "title": title,
                "asin": item_id_match.group(1) if item_id_match else None,
                "url": link,
                "price": _parse_price(raw_price),
                "currency": "EUR" if raw_price else None,
                "image": image_match.group(1) if image_match else None,
                "seller": None,
                "brand": None,
                "rating": None,
                "source": "ebay_it",
            }
        )

    return results


def sort_products(products: Sequence[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
    indexed = list(enumerate(products))

    if sort_by == "lowest_price":
        sorted_indexed = sorted(
            indexed,
            key=lambda pair: (
                pair[1].get("price") is None,
                pair[1].get("price") if pair[1].get("price") is not None else float("inf"),
                pair[0],
            ),
        )
        return [item for _, item in sorted_indexed]

    if sort_by == "highest_rating":
        sorted_indexed = sorted(
            indexed,
            key=lambda pair: (
                pair[1].get("rating") is None,
                -(pair[1].get("rating") or 0.0),
                pair[0],
            ),
        )
        return [item for _, item in sorted_indexed]

    return [item for _, item in indexed]


def _dedupe_products(products: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for product in products:
        key = product.get("asin") or product.get("url") or product.get("title")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(product)
    return deduped


class AmazonItSource(KeywordSearchSource):
    source_name = "amazon_it"

    @staticmethod
    def build_search_url(query: str) -> str:
        return f"https://www.amazon.it/s?k={quote_plus(query)}"

    @staticmethod
    def _is_valid_amazon_it_url(url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return host.endswith("amazon.it")

    def search(
        self,
        query: Optional[str] = None,
        search_url: Optional[str] = None,
        sort_by: str = "best_match",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        if not self.config.enabled:
            return []

        resolved_url = (search_url or "").strip()
        if resolved_url:
            if not self._is_valid_amazon_it_url(resolved_url):
                logger.warning("Ignoring unsupported Amazon search URL: %s", resolved_url)
                return []
        elif query:
            resolved_url = self.build_search_url(query)
        else:
            return []

        payload = self._request_text(resolved_url)
        if not payload:
            return []

        parsed = parse_amazon_it_search_html(payload, resolved_url)
        return sort_products(parsed, sort_by)[:limit]


class EbayItSource(KeywordSearchSource):
    source_name = "ebay_it"

    @staticmethod
    def build_search_url(query: str) -> str:
        return f"https://www.ebay.it/sch/i.html?_nkw={quote_plus(query)}&_rss=1"

    def search(
        self,
        query: Optional[str] = None,
        search_url: Optional[str] = None,
        sort_by: str = "best_match",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        if not self.config.enabled or not query:
            return []

        payload = self._request_text(self.build_search_url(query))
        if not payload:
            return []

        parsed = parse_ebay_it_rss(payload)
        return sort_products(parsed, sort_by)[:limit]


def build_source_registry() -> Dict[str, KeywordSearchSource]:
    amazon_config = SourceConfig(
        enabled=_bool_env("ENABLE_AMAZON_IT", True),
        timeout=_int_env("AMAZON_IT_TIMEOUT", 12),
        retries=_int_env("AMAZON_IT_RETRIES", 2),
        backoff_seconds=_float_env("AMAZON_IT_BACKOFF_SECONDS", 1.0),
        rate_limit_seconds=_float_env("AMAZON_IT_RATE_LIMIT_SECONDS", 1.5),
        proxy=os.getenv("AMAZON_IT_PROXY"),
    )
    ebay_config = SourceConfig(
        enabled=_bool_env("ENABLE_EBAY_IT", True),
        timeout=_int_env("EBAY_IT_TIMEOUT", 12),
        retries=_int_env("EBAY_IT_RETRIES", 2),
        backoff_seconds=_float_env("EBAY_IT_BACKOFF_SECONDS", 1.0),
        rate_limit_seconds=_float_env("EBAY_IT_RATE_LIMIT_SECONDS", 1.0),
        proxy=os.getenv("EBAY_IT_PROXY"),
    )
    return {
        "amazon_it": AmazonItSource(amazon_config),
        "ebay_it": EbayItSource(ebay_config),
    }


def search_market_products(
    query: Optional[str],
    amazon_search_url: Optional[str],
    source_names: Sequence[str],
    strategy: str = "merge",
    sort_by: str = "best_match",
    limit: int = 10,
    source_registry: Optional[Dict[str, KeywordSearchSource]] = None,
) -> List[Dict[str, Any]]:
    registry = source_registry or build_source_registry()
    selected = [name.strip() for name in source_names if name.strip()]
    all_products: List[Dict[str, Any]] = []

    for source_name in selected:
        source = registry.get(source_name)
        if not source:
            logger.warning("Unknown source requested: %s", source_name)
            continue

        products = source.search(
            query=query,
            search_url=amazon_search_url,
            sort_by=sort_by,
            limit=limit,
        )
        logger.info("Source %s produced %d candidate(s)", source_name, len(products))
        if strategy == "fallback" and products:
            return products[:limit]
        all_products.extend(products)

    merged = _dedupe_products(all_products)
    return sort_products(merged, sort_by)[:limit]
