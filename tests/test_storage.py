import sqlite3

from common.storage import save_records_sqlite


def test_save_records_sqlite(tmp_path):
    db_path = tmp_path / "results.db"
    records = [
        {
            "ean": "1111111111111",
            "product_name": "Test Product",
            "brand": "Test Brand",
            "category": "Test Category",
            "price": 19.99,
            "currency": "EUR",
            "source": "test",
            "market": "IT",
            "scraped_at": "2026-01-01T00:00:00+00:00",
        }
    ]

    written = save_records_sqlite(str(db_path), records)

    assert written == 1
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT ean, product_name, market FROM products").fetchone()

    assert row == ("1111111111111", "Test Product", "IT")
