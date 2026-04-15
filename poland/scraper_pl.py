from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Optional

sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.open_food_facts import OpenFoodFactsClient
from common.open_product_data import OpenProductDataClient
from common.storage import export_records_csv, save_records_sqlite
from poland.sources_pl import allegro_device_flow_instructions, allegro_search_scaffold, scrape_ceneo


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


def scrape_ean_pl(ean: str) -> Dict[str, object]:
    off = OpenFoodFactsClient().fetch(ean)
    allegro = allegro_search_scaffold(ean) if not off or not off.get("price") else None
    ceneo = scrape_ceneo(ean) if not allegro else None
    opd = OpenProductDataClient().fetch(ean) if not off and not allegro and not ceneo else None
    return _merge_records(ean, "PL", [off, allegro, ceneo, opd])


def main() -> None:
    parser = argparse.ArgumentParser(description="EAN scraper for Poland market")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ean", help="Single EAN code")
    group.add_argument("--batch", help="Path to batch file (one EAN per line)")
    parser.add_argument("--db", default="data/results.db", help="SQLite output path")
    parser.add_argument("--csv", default=None, help="Optional CSV output path")
    parser.add_argument(
        "--allegro-help",
        action="store_true",
        help="Print OAuth2 device flow setup instructions for Allegro",
    )
    args = parser.parse_args()

    if args.allegro_help:
        print(allegro_device_flow_instructions())

    eans = _read_eans(args.ean, args.batch)
    records = [scrape_ean_pl(ean) for ean in eans]
    save_records_sqlite(args.db, records)
    if args.csv:
        export_records_csv(args.csv, records)

    for record in records:
        print(record)


if __name__ == "__main__":
    main()
