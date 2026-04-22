from scripts.run_scrape import is_ean_query, resolve_ean, select_best_candidate


def test_is_ean_query_accepts_8_or_13_digits():
    assert is_ean_query("12345678")
    assert is_ean_query("1234567890123")


def test_is_ean_query_rejects_other_formats():
    assert not is_ean_query("1234567")
    assert not is_ean_query("123456789012")
    assert not is_ean_query("EAN12345678")
    assert not is_ean_query("nutella")


def test_select_best_candidate_prefers_closest_name():
    query = "Nutella Biscuit"
    candidates = [
        {"ean": "11111111", "product_name": "Tomato sauce"},
        {"ean": "22222222", "product_name": "Nutella biscuits 304g"},
        {"ean": "33333333", "product_name": "Chocolate cream"},
    ]

    selected = select_best_candidate(query, candidates)

    assert selected is not None
    assert selected["ean"] == "22222222"


def test_resolve_ean_skips_search_for_direct_ean(monkeypatch):
    class _DummyClient:
        def search(self, query, page_size=20):  # pragma: no cover - should never run
            raise AssertionError("search should not be called for EAN query")

    monkeypatch.setattr("scripts.run_scrape.OpenFoodFactsClient", lambda: _DummyClient())

    assert resolve_ean("5901234123457", "PL") == "5901234123457"


def test_resolve_ean_from_text_uses_best_candidate(monkeypatch):
    class _DummyClient:
        def search(self, query, page_size=20):
            return [
                {"ean": "4008400402220", "product_name": "Cream Cracker"},
                {"ean": "8000500310427", "product_name": "Nutella Biscuits"},
            ]

    monkeypatch.setattr("scripts.run_scrape.OpenFoodFactsClient", lambda: _DummyClient())

    assert resolve_ean("nutella biscuit", "IT", page_size=5) == "8000500310427"
