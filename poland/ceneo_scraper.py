from __future__ import annotations

from typing import List
from urllib.parse import quote_plus, urljoin

from common.html_utils import first_attr, make_soup, select_text, stable_nodes
from common.models import Offer
from common.normalization import parse_currency_amount, parse_delivery_cost
from common.scraper_base import ScraperBase


class CeneoScraper(ScraperBase):
    def __init__(self) -> None:
        super().__init__(env_prefix="CENEO")

    @staticmethod
    def build_search_url(query: str) -> str:
        return f"https://www.ceneo.pl/;szukaj-{quote_plus(query)}"

    def search(self, query: str, limit: int = 10) -> List[Offer]:
        html = self.http.get_text(self.build_search_url(query))
        if not html:
            return []

        soup = make_soup(html)
        cards = stable_nodes(
            soup,
            (
                "div.cat-prod-row",
                "article[data-productid]",
                "div[data-testid='product-card']",
            ),
        )

        offers: List[Offer] = []
        for card in cards[:limit]:
            title = select_text(card, (".cat-prod-row-name a", "a[title]", "h2 a", "h2"))
            link = first_attr(card, (".cat-prod-row-name a", "h2 a", "a[href]"), "href")
            price_text = select_text(card, (".price", ".product-price", "[class*='price']"))
            delivery_text = select_text(card, ("[class*='delivery']", "[class*='shipping']", "[class*='dostawa']"))

            if not title or not link:
                continue

            amount, currency = parse_currency_amount(price_text or "", default_currency="PLN")
            delivery_cost, delivery_currency = parse_delivery_cost(delivery_text or "", default_currency=currency)
            resolved_currency = delivery_currency if delivery_cost is not None and delivery_currency else currency
            offers.append(
                Offer(
                    product_name=title,
                    source="Ceneo",
                    link=urljoin("https://www.ceneo.pl", link),
                    item_price=amount,
                    currency=resolved_currency,
                    delivery_cost=delivery_cost,
                )
            )

        return offers


def scrape_ceneo(query: str, limit: int = 10) -> List[Offer]:
    return CeneoScraper().search(query=query, limit=limit)
