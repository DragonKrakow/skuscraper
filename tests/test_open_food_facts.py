from common.open_food_facts import OpenFoodFactsClient


def test_parse_off_product_success():
    payload = {
        "status": 1,
        "product": {
            "product_name": "Sample Product",
            "brands": "Brand A,Brand B",
            "categories_tags": ["en:snacks"],
        },
    }

    parsed = OpenFoodFactsClient.parse_product(payload, "1234567890123")

    assert parsed is not None
    assert parsed["ean"] == "1234567890123"
    assert parsed["product_name"] == "Sample Product"
    assert parsed["brand"] == "Brand A"
    assert parsed["category"] == "en:snacks"
    assert parsed["source"] == "open_food_facts"


def test_parse_off_product_not_found():
    assert OpenFoodFactsClient.parse_product({"status": 0}, "123") is None
