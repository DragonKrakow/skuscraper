from __future__ import annotations

import argparse
import re
from difflib import SequenceMatcher
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, Optional

sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.open_food_facts import OpenFoodFactsClient
from common.storage import export_records_csv
from italy.scraper_it import scrape_ean_it
from poland.scraper_pl import scrape_ean_pl

EAN_PATTERN = re.compile(r"^(?:\d{8}|\d{13})$")


def is_ean_query(query: str) -> bool:
    return bool(EAN_PATTERN.fullmatch(query.strip()))


def _score_candidate(query: str, candidate: Dict[str, Any]) -> tuple[float, int, str]:
    normalized_query = query.strip().lower()
    name = str(candidate.get("product_name") or "").strip().lower()
    ean = str(candidate.get("ean") or "")
    ratio = SequenceMatcher(None, normalized_query, name).ratio() if name else 0.0
    contains_bonus = 0.2 if normalized_query and normalized_query in name else 0.0
    return (ratio + contains_bonus, -len(name), ean)


def select_best_candidate(query: str, candidates: Iterable[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    ordered = sorted(candidates, key=lambda candidate: _score_candidate(query, candidate), reverse=True)
    return ordered[0] if ordered else None


def resolve_ean(query: str, market: str, page_size: int = 20) -> str:
    normalized = query.strip()
    if is_ean_query(normalized):
        return normalized

    candidates = OpenFoodFactsClient().search(normalized, page_size=page_size)
    best = select_best_candidate(normalized, candidates)
    if not best or not best.get("ean"):
        raise ValueError(f"No matching EAN candidate found for query: {query!r} in market {market}")
    return str(best["ean"])


def scrape_market_ean(market: str, ean: str) -> Dict[str, Any]:
    if market == "IT":
        return scrape_ean_it(ean)
    if market == "PL":
        return scrape_ean_pl(ean)
    raise ValueError(f"Unsupported market: {market}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve product query to EAN and scrape market data to CSV")
    parser.add_argument("--market", choices=["IT", "PL"], required=True, help="Market to scrape")
    parser.add_argument("--query", required=True, help="EAN code (8/13 digits) or free-text product query")
    parser.add_argument("--csv", default="outputs/results.csv", help="Output CSV path")
    parser.add_argument("--search-limit", type=int, default=20, help="Max Open Food Facts candidates for text query")
    args = parser.parse_args()

    if args.search_limit < 1:
        parser.error("--search-limit must be >= 1")

    ean = resolve_ean(args.query, args.market, page_size=args.search_limit)
    record = scrape_market_ean(args.market, ean)
    export_records_csv(args.csv, [record])
    print(f"Resolved query={args.query!r} to ean={ean} for market={args.market}. CSV: {args.csv}")


if __name__ == "__main__":
    main()
