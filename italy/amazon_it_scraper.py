from __future__ import annotations

from typing import List
from urllib.parse import quote_plus, urljoin

from common.models import Offer
from common.normalization import parse_currency_amount, parse_delivery_cost
from common.scraper_base import ScraperBase

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - optional runtime dependency safety
    sync_playwright = None


class AmazonItScraper(ScraperBase):
    def __init__(self) -> None:
        super().__init__(env_prefix="AMAZON_IT")

    @staticmethod
    def build_search_url(query: str) -> str:
        return f"https://www.amazon.it/s?k={quote_plus(query)}"

    def search(self, query: str, limit: int = 10) -> List[Offer]:
        if sync_playwright is None:
            return []

        launch_options, context_options = self.playwright_launch_options()
        context_options = {**context_options, "locale": "it-IT", "timezone_id": "Europe/Rome"}

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**launch_options)
            context = browser.new_context(**context_options)
            page = context.new_page()
            page.goto(self.build_search_url(query), wait_until="domcontentloaded")
            page.wait_for_timeout(1800)

            cards = page.query_selector_all("div[data-component-type='s-search-result']")
            offers: List[Offer] = []

            for card in cards:
                title_el = card.query_selector("h2 span")
                link_el = card.query_selector("h2 a[href]")
                if not title_el or not link_el:
                    continue

                title = (title_el.inner_text() or "").strip()
                link = urljoin("https://www.amazon.it", link_el.get_attribute("href") or "")
                if not title or not link:
                    continue

                price_text = ""
                for selector in ("span.a-price span.a-offscreen", "span.a-offscreen", "[aria-label*='€']"):
                    price_el = card.query_selector(selector)
                    if price_el:
                        price_text = (price_el.inner_text() or "").strip()
                        if price_text:
                            break

                combined_text = (card.inner_text() or "").strip()
                amount, currency = parse_currency_amount(price_text, default_currency="EUR")
                delivery_cost, delivery_currency = parse_delivery_cost(combined_text, default_currency=currency)
                resolved_currency = delivery_currency if delivery_cost is not None and delivery_currency else currency
                offers.append(
                    Offer(
                        product_name=title,
                        source="Amazon.it",
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


def scrape_amazon_it(query: str, limit: int = 10) -> List[Offer]:
    return AmazonItScraper().search(query=query, limit=limit)
