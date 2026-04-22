from __future__ import annotations

import argparse
import re
from pathlib import Path
import sys
from typing import Any, Dict, List

sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.storage import export_records_csv
from common.exporter import export_offers_csv
from common.models import Offer

from italy.scraper_it import scrape_ean_it
from poland.scraper_pl import scrape_ean_pl

from italy.amazon_it_scraper import scrape_amazon_it
from italy.ebay_it_scraper import scrape_ebay_it
from poland.allegro_scraper import scrape_allegro
from poland.ceneo_scraper import scrape_ceneo

EAN_PATTERN = re.compile(r"^(?:\d{8}|\d{13})$")


def is_ean_query(query: str) -> bool:
    return bool(EAN_PATTERN.fullmatch(query.strip()))


def scrape_ean(market: str, ean: str) -> Dict[str, Any]:
    if market == "IT":
        return scrape_ean_it(ean)
    if market == "PL":
        return scrape_ean_pl(ean)
    raise ValueError(f"Unsupported market: {market}")


def scrape_keyword_offers(market: str, query: str, limit: int) -> List[Offer]:
    if market == "IT":
        offers: List[Offer] = []
        offers.extend(scrape_amazon_it(query, limit) or [])
        offers.extend(scrape_ebay_it(query, limit) or [])
        return offers

    if market == "PL":
        offers: List[Offer] = []
        offers.extend(scrape_allegro(query, limit) or [])
        offers.extend(scrape_ceneo(query, limit) or [])
        return offers

    raise ValueError(f"Unsupported market: {market}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape product to CSV (EAN or free-text).")
    parser.add_argument("--market", choices=["IT", "PL"], required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--csv", default="outputs/results.csv")
    parser.add_argument("--limit", type=int, default=25, help="Free-text: max rows per source")
    args = parser.parse_args()

    query = args.query.strip()

    # EAN mode -> existing per-market EAN scrapers (records schema)
    if is_ean_query(query):
        record = scrape_ean(args.market, query)
        export_records_csv(args.csv, [record])
        print(f"EAN mode: market={args.market} ean={query}. CSV: {args.csv}")
        return

    # Free-text mode -> keyword offer scrapers (offers schema)
    offers = scrape_keyword_offers(args.market, query, args.limit)

    # Always write a CSV so the artifact upload never fails (header-only if empty)
    written = export_offers_csv(args.csv, offers)
    print(f"Keyword mode: market={args.market} query={query!r} offers_written={written}. CSV: {args.csv}")


if __name__ == "__main__":
    main()
