from __future__ import annotations

import csv
import os
from typing import Iterable

from common.models import Offer

CSV_COLUMNS = ["Product Name", "Source", "Link", "Item Price", "Currency", "Delivery Cost"]


def export_offers_csv(csv_path: str, offers: Iterable[Offer]) -> int:
    rows = [
        {
            "Product Name": offer.product_name,
            "Source": offer.source,
            "Link": offer.link,
            "Item Price": offer.item_price,
            "Currency": offer.currency,
            "Delivery Cost": offer.delivery_cost,
        }
        for offer in offers
    ]

    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
