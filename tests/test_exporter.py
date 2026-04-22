import csv

from common.exporter import CSV_COLUMNS, export_offers_csv
from common.models import Offer


def test_export_offers_csv_columns_exact(tmp_path) -> None:
    csv_path = tmp_path / "offers.csv"
    offers = [
        Offer(
            product_name="Test Product",
            source="Ceneo",
            link="https://example.test/item",
            item_price=10.5,
            currency="PLN",
            delivery_cost=4.0,
        )
    ]

    written = export_offers_csv(str(csv_path), offers)
    assert written == 1

    with open(csv_path, newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
        assert rows[0]["Product Name"] == "Test Product"
        assert rows[0]["Currency"] == "PLN"

    with open(csv_path, encoding="utf-8") as file:
        header_line = file.readline().strip()
        assert header_line == ",".join(CSV_COLUMNS)
