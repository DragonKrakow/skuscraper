from __future__ import annotations

import argparse
from datetime import datetime, timezone
import logging
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Optional

sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.open_food_facts import OpenFoodFactsClient
from common.open_product_data import OpenProductDataClient
from common.storage import export_records_csv, save_records_sqlite
from italy.market_sources import search_market_products
from italy.sources_it import scrape_amazon_it_placeholder, scrape_trovaprezzi

logger = logging.getLogger(__name__)


def _read_eans(single_ean: Optional[str], batch_file: Optional[str]) -> List[str]:
    if single_ean:
        return [single_ean.strip()]
    if not batch_file:
        return []
    return [line.strip() for line in Path(batch_file).read_text(encoding="utf-8").splitlines() if line.strip()]


def _merge_records(ean: str, market: str, records: Iterable[Dict[str, object]]) -> Dict[str, object]:
    records = [r for r in records if r]
    timestamp = datetime.now(timezone.utc).isoformat()
    if not records:
        return {
            "ean": ean,
            "product_name": None,
            "brand": None,
            "category": None,
            "price": None,
            "currency": None,
            "source": "none",
            "market": market,
            "scraped_at": timestamp,
        }

    merged: Dict[str, object] = {"ean": ean, "market": market, "scraped_at": timestamp}
    for field in ["product_name", "brand", "category", "price", "currency"]:
        merged[field] = next((r.get(field) for r in records if r.get(field) not in (None, "")), None)
    merged["source"] = ",".join(dict.fromkeys(str(r.get("source")) for r in records if r.get("source")))
    return merged


def scrape_ean_it(ean: str) -> Dict[str, object]:
    off = OpenFoodFactsClient().fetch(ean)
    opd = OpenProductDataClient().fetch(ean) if not off or not off.get("product_name") else None
    tro = scrape_trovaprezzi(ean) if not off or not off.get("price") else None
    ama = scrape_amazon_it_placeholder(ean)
    return _merge_records(ean, "IT", [off, opd, tro, ama])


def scrape_query_it(
    query: Optional[str],
    search_url: Optional[str],
    source_names: List[str],
    strategy: str,
    sort_by: str,
    limit: int,
) -> List[Dict[str, object]]:
    products = search_market_products(
        query=query,
        amazon_search_url=search_url,
        source_names=source_names,
        strategy=strategy,
        sort_by=sort_by,
        limit=limit,
    )
    timestamp = datetime.now(timezone.utc).isoformat()
    records: List[Dict[str, object]] = []
    for item in products:
        records.append(
            {
                "ean": None,
                "product_name": item.get("title"),
                "brand": item.get("brand"),
                "category": None,
                "price": item.get("price"),
                "currency": item.get("currency"),
                "source": item.get("source"),
                "market": "IT",
                "scraped_at": timestamp,
                "asin": item.get("asin"),
                "url": item.get("url"),
                "image": item.get("image"),
                "rating": item.get("rating"),
                "seller": item.get("seller"),
            }
        )
    return records


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="EAN scraper for Italy market")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ean", help="Single EAN code")
    group.add_argument("--batch", help="Path to batch file (one EAN per line)")
    group.add_argument("--query", help="Keyword query for marketplace discovery")
    group.add_argument("--search-url", help="Amazon.it search URL (manual link mode)")
    parser.add_argument("--db", default="data/results.db", help="SQLite output path")
    parser.add_argument("--csv", default=None, help="Optional CSV output path")
    parser.add_argument(
        "--sources",
        default="amazon_it,ebay_it",
        help="Comma-separated sources to use (amazon_it, ebay_it)",
    )
    parser.add_argument(
        "--strategy",
        choices=["merge", "fallback"],
        default="merge",
        help="Source strategy: merge all selected sources or fallback by order",
    )
    parser.add_argument(
        "--sort",
        choices=["best_match", "lowest_price", "highest_rating"],
        default="best_match",
        help="Deterministic result sorting",
    )
    parser.add_argument("--limit", type=int, default=10, help="Max number of product candidates")
    args = parser.parse_args()

    if args.query or args.search_url:
        sources = [s.strip() for s in args.sources.split(",") if s.strip()]
        records = scrape_query_it(
            query=args.query,
            search_url=args.search_url,
            source_names=sources,
            strategy=args.strategy,
            sort_by=args.sort,
            limit=max(1, args.limit),
        )
    else:
        eans = _read_eans(args.ean, args.batch)
        records = [scrape_ean_it(ean) for ean in eans]

    save_records_sqlite(args.db, records)
    if args.csv:
        export_records_csv(args.csv, records)

    for record in records:
        logger.info("Result from source=%s title=%s", record.get("source"), record.get("product_name"))
        print(record)


if __name__ == "__main__":
    main()
