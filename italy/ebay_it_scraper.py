from __future__ import annotations

from typing import List
from urllib.parse import quote_plus

from common.html_utils import first_attr, make_soup, select_text, stable_nodes
from common.models import Offer
from common.normalization import parse_currency_amount, parse_delivery_cost
from common.scraper_base import ScraperBase

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - optional runtime dependency safety
    sync_playwright = None


class EbayItScraper(ScraperBase):
    def __init__(self) -> None:
        super().__init__(env_prefix="EBAY_IT")

    @staticmethod
    def build_search_url(query: str) -> str:
        return f"https://www.ebay.it/sch/i.html?_nkw={quote_plus(query)}"

    def search(self, query: str, limit: int = 10) -> List[Offer]:
        offers = self._search_via_requests(query=query, limit=limit)
        if offers:
            return offers
        return self._search_via_playwright(query=query, limit=limit)

    def _search_via_requests(self, query: str, limit: int) -> List[Offer]:
        html = self.http.get_text(self.build_search_url(query))
        if not html:
            return []

        soup = make_soup(html)
        cards = stable_nodes(soup, ("li.s-item", "div.s-item__wrapper", "article"))

        offers: List[Offer] = []
        for card in cards:
            title = select_text(card, (".s-item__title", "h3", "[role='heading']"))
            link = first_attr(card, (".s-item__link", "a[href]"), "href")
            price_text = select_text(card, (".s-item__price", "[class*='price']"))
            delivery_text = select_text(card, (".s-item__shipping", "[class*='shipping']"))

            if not title or not link:
                continue

            amount, currency = parse_currency_amount(price_text or "", default_currency="EUR")
            delivery_cost, delivery_currency = parse_delivery_cost(delivery_text or "", default_currency=currency)
            offers.append(
                Offer(
                    product_name=title,
                    source="eBay.it",
                    link=link,
                    item_price=amount,
                    currency=delivery_currency or currency,
                    delivery_cost=delivery_cost,
                )
            )
            if len(offers) >= limit:
                break

        return offers

    def _search_via_playwright(self, query: str, limit: int) -> List[Offer]:
        if sync_playwright is None:
            return []

        launch_options, context_options = self.playwright_launch_options()
        context_options = {**context_options, "locale": "it-IT", "timezone_id": "Europe/Rome"}

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**launch_options)
            context = browser.new_context(**context_options)
            page = context.new_page()
            page.goto(self.build_search_url(query), wait_until="domcontentloaded")
            page.wait_for_timeout(1200)

            cards = page.query_selector_all("li.s-item")
            offers: List[Offer] = []
            for card in cards:
                title_el = card.query_selector(".s-item__title") or card.query_selector("h3")
                link_el = card.query_selector("a.s-item__link") or card.query_selector("a[href]")
                if not title_el or not link_el:
                    continue

                title = (title_el.inner_text() or "").strip()
                link = link_el.get_attribute("href") or ""
                if not title or not link:
                    continue

                price_text = (card.query_selector(".s-item__price") or card).inner_text() or ""
                shipping_text = (card.query_selector(".s-item__shipping") or card).inner_text() or ""
                amount, currency = parse_currency_amount(price_text, default_currency="EUR")
                delivery_cost, delivery_currency = parse_delivery_cost(shipping_text, default_currency=currency)
                offers.append(
                    Offer(
                        product_name=title,
                        source="eBay.it",
                        link=link,
                        item_price=amount,
                        currency=delivery_currency or currency,
                        delivery_cost=delivery_cost,
                    )
                )
                if len(offers) >= limit:
                    break

            context.close()
            browser.close()
            return offers


def scrape_ebay_it(query: str, limit: int = 10) -> List[Offer]:
    return EbayItScraper().search(query=query, limit=limit)
