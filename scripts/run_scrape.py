from __future__ import annotations

import argparse
import csv
import difflib
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.storage import export_records_csv
from common.exporter import export_offers_csv
from common.models import Offer
from common.open_food_facts import OpenFoodFactsClient

from italy.scraper_it import scrape_ean_it
from poland.scraper_pl import scrape_ean_pl

from italy.amazon_it_scraper import scrape_amazon_it
from italy.ebay_it_scraper import scrape_ebay_it
from poland.allegro_scraper import scrape_allegro
from poland.ceneo_scraper import scrape_ceneo

EAN_PATTERN = re.compile(r"^(?:\d{8}|\d{13})$")

# Hertwill CSV output columns
HERTWILL_CSV_COLUMNS = [
    "brand",
    "product_name",
    "discount",
    "wholesale_pln",
    "subscriber_pln",
    "hertwill_url",
    "market",
    "scraped_at",
    "source",
    "link",
    "item_price",
    "currency",
    "delivery_cost",
    "item_price_pln",
]


def is_ean_query(query: str) -> bool:
    return bool(EAN_PATTERN.fullmatch(query.strip()))


def select_best_candidate(
    query: str, candidates: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Return the candidate whose product_name best matches the query.

    When scores are equal the candidate with the lexicographically highest EAN
    is returned (stable tie-break).
    """
    if not candidates:
        return None
    query_lower = query.lower()

    def _score(candidate: Dict[str, Any]):
        name = (candidate.get("product_name") or "").lower()
        ratio = difflib.SequenceMatcher(None, query_lower, name).ratio()
        ean = candidate.get("ean") or ""
        return (ratio, ean)

    return max(candidates, key=_score)


def resolve_ean(
    query: str, market: str, page_size: int = 20
) -> Optional[str]:
    """Return an EAN for *query*.

    If *query* is already a valid EAN it is returned as-is.  Otherwise
    OpenFoodFacts is searched and the best-matching product's EAN is returned,
    or ``None`` when nothing is found.
    """
    if is_ean_query(query):
        return query
    client = OpenFoodFactsClient()
    candidates = client.search(query, page_size=page_size)
    best = select_best_candidate(query, candidates)
    return best["ean"] if best else None


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


# ---------------------------------------------------------------------------
# Hertwill helpers
# ---------------------------------------------------------------------------

_PLN_NOISE = re.compile(r"[zł\s\u00a0]+")


def parse_pln_price(raw: str) -> Optional[float]:
    """Parse a PLN price string such as ``'174,02 zł'`` or ``'1 234.56 zł'``."""
    cleaned = _PLN_NOISE.sub("", (raw or "").strip())
    # Normalise decimal separator: if both , and . present keep last as decimal
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def load_hertwill_csv(csv_path: str) -> List[Dict[str, str]]:
    """Load hertwill product rows from a CSV file.

    Expected columns (case-insensitive strip):
        Brand, Product Name, Discount, Wholesale Price (PLN),
        Subscriber Price (PLN), URL
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"Hertwill CSV not found: {csv_path}")

    rows: List[Dict[str, str]] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            # Normalise keys (skip None keys from extra commas)
            normalised = {k.strip(): (v or "").strip() for k, v in row.items() if k is not None}
            rows.append(normalised)
    return rows


def scrape_hertwill_mode(
    market: str,
    csv_path: str,
    output_csv: str,
    limit: int = 10,
) -> None:
    """Run hertwill batch scraping and write a combined offers CSV."""
    rows = load_hertwill_csv(csv_path)
    print(f"Hertwill mode: market={market} products={len(rows)} limit_per_source={limit}")

    all_offer_rows: List[Dict[str, Any]] = []
    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for row in rows:
        brand = row.get("Brand", "")
        product_name = row.get("Product Name", "")
        discount = row.get("Discount", "")
        wholesale_pln = parse_pln_price(row.get("Wholesale Price (PLN)", ""))
        subscriber_pln = parse_pln_price(row.get("Subscriber Price (PLN)", ""))
        hertwill_url = row.get("URL", "")

        if not product_name:
            continue

        # Collect offers per source
        source_offers: Dict[str, List[Offer]] = {}
        if market == "IT":
            source_offers["Amazon.it"] = scrape_amazon_it(product_name, limit) or []
            source_offers["eBay.it"] = scrape_ebay_it(product_name, limit) or []
        elif market == "PL":
            source_offers["Allegro"] = scrape_allegro(product_name, limit) or []
            source_offers["Ceneo"] = scrape_ceneo(product_name, limit) or []
        else:
            raise ValueError(f"Unsupported market: {market}")

        for source_name, offers in source_offers.items():
            print(
                f"  {product_name!r}: source={source_name} offers={len(offers)}"
            )
            for offer in offers:
                item_price_pln: Optional[float] = None
                if offer.currency and offer.currency.upper() == "PLN":
                    item_price_pln = offer.item_price
                # Leave blank when currency != PLN (no conversion table)

                all_offer_rows.append(
                    {
                        "brand": brand,
                        "product_name": product_name,
                        "discount": discount,
                        "wholesale_pln": wholesale_pln,
                        "subscriber_pln": subscriber_pln,
                        "hertwill_url": hertwill_url,
                        "market": market,
                        "scraped_at": scraped_at,
                        "source": offer.source,
                        "link": offer.link,
                        "item_price": offer.item_price,
                        "currency": offer.currency,
                        "delivery_cost": offer.delivery_cost,
                        "item_price_pln": item_price_pln,
                    }
                )

    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=HERTWILL_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(all_offer_rows)

    print(
        f"Hertwill mode done: offers_written={len(all_offer_rows)}. CSV: {output_csv}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape product to CSV (EAN, free-text, or hertwill batch).")
    parser.add_argument("--market", choices=["IT", "PL"], required=True)
    parser.add_argument(
        "--mode",
        choices=["auto", "ean", "keyword", "hertwill"],
        default="auto",
        help=(
            "Scraping mode: 'auto' detects EAN vs keyword from --query, "
            "'ean' forces EAN lookup, 'keyword' forces free-text search, "
            "'hertwill' reads products from --csv-path."
        ),
    )
    parser.add_argument("--query", default="", help="Product query (EAN or free text); used in auto/ean/keyword modes")
    parser.add_argument("--csv-path", default="", help="Path to hertwill products CSV (required for --mode hertwill)")
    parser.add_argument("--csv", default="outputs/results.csv")
    parser.add_argument("--limit", type=int, default=25, help="Max offers per source")
    args = parser.parse_args()

    mode = args.mode

    # Hertwill batch mode
    if mode == "hertwill":
        if not args.csv_path:
            parser.error("--csv-path is required when --mode hertwill")
        scrape_hertwill_mode(args.market, args.csv_path, args.csv, args.limit)
        return

    query = args.query.strip()
    if not query:
        parser.error("--query is required for auto/ean/keyword modes")

    # EAN mode (explicit or auto-detected)
    if mode == "ean" or (mode == "auto" and is_ean_query(query)):
        record = scrape_ean(args.market, query)
        export_records_csv(args.csv, [record])
        print(f"EAN mode: market={args.market} ean={query}. CSV: {args.csv}")
        return

    # Keyword / free-text mode
    offers = scrape_keyword_offers(args.market, query, args.limit)

    # Always write a CSV so the artifact upload never fails (header-only if empty)
    written = export_offers_csv(args.csv, offers)
    print(f"Keyword mode: market={args.market} query={query!r} offers_written={written}. CSV: {args.csv}")


if __name__ == "__main__":
    main()
