from __future__ import annotations

import csv
import os
import sqlite3
from typing import Any, Dict, Iterable, List

SCHEMA_FIELDS = [
    "ean",
    "product_name",
    "brand",
    "category",
    "price",
    "currency",
    "source",
    "market",
    "scraped_at",
]


def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    return {field: record.get(field) for field in SCHEMA_FIELDS}


def init_db(db_path: str) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ean TEXT,
                product_name TEXT,
                brand TEXT,
                category TEXT,
                price REAL,
                currency TEXT,
                source TEXT,
                market TEXT,
                scraped_at TEXT
            )
            """
        )
        conn.commit()


def save_records_sqlite(db_path: str, records: Iterable[Dict[str, Any]]) -> int:
    normalized: List[Dict[str, Any]] = [normalize_record(r) for r in records]
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO products (
                ean, product_name, brand, category, price, currency, source, market, scraped_at
            ) VALUES (
                :ean, :product_name, :brand, :category, :price, :currency, :source, :market, :scraped_at
            )
            """,
            normalized,
        )
        conn.commit()
    return len(normalized)


def export_records_csv(csv_path: str, records: Iterable[Dict[str, Any]]) -> int:
    normalized: List[Dict[str, Any]] = [normalize_record(r) for r in records]
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    write_header = not os.path.exists(csv_path)

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SCHEMA_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerows(normalized)

    return len(normalized)
