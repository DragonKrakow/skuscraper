from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import requests

from common.models import Offer
from common.normalization import parse_currency_amount, parse_delivery_cost
from common.scraper_base import ScraperBase

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - optional runtime dependency safety
    sync_playwright = None


class AllegroScraper(ScraperBase):
    LISTING_URL_TEMPLATE = "https://www.allegro.pl/listing?string={query}"

    def __init__(self) -> None:
        super().__init__(env_prefix="ALLEGRO")

    def search(self, query: str, limit: int = 10) -> List[Offer]:
        offers = self._search_via_api(query=query, limit=limit)
        if offers:
            return offers
        return self._search_via_playwright(query=query, limit=limit)

    def _search_via_api(self, query: str, limit: int) -> List[Offer]:
        token = os.getenv("ALLEGRO_ACCESS_TOKEN")
        if not token:
            return []

        try:
            response = requests.get(
                "https://api.allegro.pl/offers/listing",
                params={"phrase": query},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.allegro.public.v1+json",
                    **self.headers,
                },
                timeout=self.http.config.timeout,
            )
            response.raise_for_status()
            payload: Dict[str, Any] = response.json()
        except (requests.RequestException, ValueError):
            return []

        offers_data = ((payload.get("items") or {}).get("regular") or [])[:limit]
        offers: List[Offer] = []
        for item in offers_data:
            price = ((item.get("sellingMode") or {}).get("price") or {})
            raw_amount = price.get("amount")
            try:
                amount = float(raw_amount) if raw_amount else None
            except (TypeError, ValueError):
                amount = None
            currency = price.get("currency") or "PLN"
            offers.append(
                Offer(
                    product_name=item.get("name") or query,
                    source="Allegro",
                    link=(item.get("url") or "").strip()
                    or self.LISTING_URL_TEMPLATE.format(query=quote_plus(query)),
                    item_price=amount,
                    currency=currency,
                    delivery_cost=None,
                )
            )
        return offers

    def _search_via_playwright(self, query: str, limit: int) -> List[Offer]:
        if sync_playwright is None:
            return []

        launch_options, context_options = self.playwright_launch_options()
        context_options = {**context_options, "locale": "pl-PL", "timezone_id": "Europe/Warsaw"}

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**launch_options)
            context = browser.new_context(**context_options)
            page = context.new_page()
            page.goto(self.LISTING_URL_TEMPLATE.format(query=quote_plus(query)), wait_until="domcontentloaded")
            page.wait_for_timeout(1500)

            card_selector = "article"
            cards = page.query_selector_all(card_selector)
            offers: List[Offer] = []

            for card in cards:
                title_el = card.query_selector("h2") or card.query_selector("[data-role='offer-title']")
                link_el = card.query_selector("a[href*='/oferta/']") or card.query_selector("a[href]")
                if not title_el or not link_el:
                    continue

                title = (title_el.inner_text() or "").strip()
                link = link_el.get_attribute("href") or ""
                if not title or not link:
                    continue

                combined_text = (card.inner_text() or "").strip()
                price_text = ""
                for selector in ("[data-role='price']", "[aria-label*='zł']", "[class*='price']"):
                    candidate = card.query_selector(selector)
                    if candidate:
                        price_text = candidate.inner_text() or ""
                        if price_text:
                            break

                amount, currency = parse_currency_amount(price_text, default_currency="PLN")
                delivery_cost, delivery_currency = parse_delivery_cost(combined_text, default_currency=currency)
                resolved_currency = delivery_currency if delivery_cost is not None and delivery_currency else currency
                offers.append(
                    Offer(
                        product_name=title,
                        source="Allegro",
                        link=link,
                        item_price=amount,
                        currency=resolved_currency,
                        delivery_cost=delivery_cost,
                    )
                )
                if len(offers) >= limit:
                    break

            context.close()
            browser.close()
            return offers


def scrape_allegro(query: str, limit: int = 10) -> List[Offer]:
    return AllegroScraper().search(query=query, limit=limit)
