import main
from common.models import Offer


def test_run_all_scrapers_parallel_contract(monkeypatch) -> None:
    def _one(query: str, limit: int):
        return [Offer("A", "Allegro", "https://a", 1.0, "PLN", 2.0)]

    def _two(query: str, limit: int):
        return [Offer("B", "Amazon.it", "https://b", 3.0, "EUR", 0.0)]

    monkeypatch.setattr(main, "SCRAPERS", {"Allegro": _one, "Amazon.it": _two})

    offers = main.run_all_scrapers("cream", limit_per_source=5)

    assert len(offers) == 2
    assert {offer.product_name for offer in offers} == {"A", "B"}
