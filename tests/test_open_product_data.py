from common.open_product_data import OpenProductDataClient


def test_parse_opd_product_success():
    payload = {
        "product": {
            "name": "OPD Product",
            "brand": "OPD Brand",
            "category": "Cosmetics",
            "price": 12.34,
            "currency": "EUR",
        }
    }

    parsed = OpenProductDataClient.parse_product(payload, "4006381333931")

    assert parsed is not None
    assert parsed["ean"] == "4006381333931"
    assert parsed["product_name"] == "OPD Product"
    assert parsed["brand"] == "OPD Brand"
    assert parsed["category"] == "Cosmetics"
    assert parsed["price"] == 12.34
    assert parsed["currency"] == "EUR"
    assert parsed["source"] == "open_product_data"


def test_parse_opd_product_not_found():
    assert OpenProductDataClient.parse_product({}, "123") is None
