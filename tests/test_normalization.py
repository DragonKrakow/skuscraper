from common.normalization import parse_currency_amount, parse_delivery_cost


def test_parse_currency_amount_pln() -> None:
    amount, currency = parse_currency_amount("129,99 zł")
    assert amount == 129.99
    assert currency == "PLN"


def test_parse_currency_amount_eur() -> None:
    amount, currency = parse_currency_amount("EUR 19.90")
    assert amount == 19.9
    assert currency == "EUR"


def test_parse_delivery_cost_keyword_match() -> None:
    amount, currency = parse_delivery_cost("spedizione 4,99 €")
    assert amount == 4.99
    assert currency == "EUR"


def test_parse_delivery_cost_free() -> None:
    amount, currency = parse_delivery_cost("dostawa gratis", default_currency="PLN")
    assert amount == 0.0
    assert currency == "PLN"
