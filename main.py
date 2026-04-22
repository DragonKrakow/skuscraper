from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List

from common.exporter import export_offers_csv
from common.models import Offer
from italy.amazon_it_scraper import scrape_amazon_it
from italy.ebay_it_scraper import scrape_ebay_it
from poland.allegro_scraper import scrape_allegro
from poland.ceneo_scraper import scrape_ceneo

logger = logging.getLogger(__name__)

SCRAPERS: Dict[str, Callable[[str, int], List[Offer]]] = {
    "Allegro": scrape_allegro,
    "Ceneo": scrape_ceneo,
    "Amazon.it": scrape_amazon_it,
    "eBay.it": scrape_ebay_it,
}


def run_all_scrapers(query: str, limit_per_source: int = 10) -> List[Offer]:
    offers: List[Offer] = []
    with ThreadPoolExecutor(max_workers=len(SCRAPERS)) as executor:
        future_map = {
            executor.submit(scraper, query, limit_per_source): source
            for source, scraper in SCRAPERS.items()
        }
        for future in as_completed(future_map):
            source = future_map[future]
            try:
                offers.extend(future.result() or [])
            except Exception as exc:
                logger.warning("%s scraper failed: %s", source, exc)
    return offers


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Competitor price analysis tool")
    parser.add_argument("--query", required=True, help="Product name or keyword query")
    parser.add_argument("--csv", required=True, help="Absolute or relative CSV output path")
    parser.add_argument("--limit", type=int, default=10, help="Max rows per source")
    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit must be >= 1")

    offers = run_all_scrapers(query=args.query, limit_per_source=args.limit)
    written = export_offers_csv(args.csv, offers)
    logger.info("Wrote %s offers to %s", written, args.csv)


if __name__ == "__main__":
    main()
