from pathlib import Path

from italy.market_sources import parse_amazon_it_search_html, parse_ebay_it_rss, search_market_products, sort_products


def _fixture(name: str) -> str:
    return (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")


def test_parse_amazon_it_search_html():
    products = parse_amazon_it_search_html(
        _fixture("amazon_it_search_sample.html"),
        "https://www.amazon.it/s?k=crema+anticellulite",
    )

    assert len(products) == 2
    assert products[0]["source"] == "amazon_it"
    assert products[0]["asin"] == "B000111111"
    assert products[0]["price"] == 44.90
    assert products[0]["rating"] == 4.6
    assert products[0]["url"] == "https://www.amazon.it/dp/B000111111"


def test_parse_ebay_it_rss():
    products = parse_ebay_it_rss(_fixture("ebay_it_search_sample.xml"))

    assert len(products) == 2
    assert products[0]["source"] == "ebay_it"
    assert products[0]["asin"] == "123456789012"
    assert products[0]["price"] == 29.99
    assert products[0]["currency"] == "EUR"
    assert products[0]["image"] == "https://i.example/eb1.jpg"


def test_sort_products_lowest_price():
    sorted_products = sort_products(
        [
            {"title": "A", "price": 12.0},
            {"title": "B", "price": None},
            {"title": "C", "price": 8.0},
        ],
        "lowest_price",
    )

    assert [p["title"] for p in sorted_products] == ["C", "A", "B"]


class _DummySource:
    def __init__(self, products):
        self.products = products

    def search(self, query=None, search_url=None, sort_by="best_match", limit=10):
        return self.products[:limit]


def test_search_market_products_fallback_prefers_first_source_with_results():
    registry = {
        "amazon_it": _DummySource([{"title": "A1", "source": "amazon_it"}]),
        "ebay_it": _DummySource([{"title": "E1", "source": "ebay_it"}]),
    }

    products = search_market_products(
        query="crema anticellulite",
        amazon_search_url=None,
        source_names=["amazon_it", "ebay_it"],
        strategy="fallback",
        source_registry=registry,  # type: ignore[arg-type]
    )

    assert len(products) == 1
    assert products[0]["source"] == "amazon_it"
