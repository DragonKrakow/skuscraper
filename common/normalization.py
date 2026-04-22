from __future__ import annotations

import re
from typing import Optional, Tuple

_CURRENCY_PATTERNS = [
    (re.compile(r"\bPLN\b|zł", re.I), "PLN"),
    (re.compile(r"\bEUR\b|€", re.I), "EUR"),
]

_AMOUNT_PATTERN = re.compile(r"(\d{1,3}(?:[\.\s]\d{3})*(?:[\.,]\d{1,2})?|\d+(?:[\.,]\d{1,2})?)")
_DELIVERY_PATTERN = re.compile(
    r"(?i)(dostawa|spedizione|delivery)[^\d€zł]{0,20}(\d{1,3}(?:[\.\s]\d{3})*(?:[\.,]\d{1,2})?|\d+(?:[\.,]\d{1,2})?)"
)


def _to_float(value: str) -> Optional[float]:
    normalized = value.replace(" ", "")
    if "," in normalized and "." in normalized:
        if normalized.rfind(",") > normalized.rfind("."):
            normalized = normalized.replace(".", "").replace(",", ".")
        else:
            normalized = normalized.replace(",", "")
    elif "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def detect_currency(text: str) -> Optional[str]:
    if not text:
        return None
    for pattern, currency in _CURRENCY_PATTERNS:
        if pattern.search(text):
            return currency
    return None


def parse_currency_amount(text: str, default_currency: Optional[str] = None) -> Tuple[Optional[float], Optional[str]]:
    if not text:
        return None, default_currency
    amount_match = _AMOUNT_PATTERN.search(text)
    amount = _to_float(amount_match.group(1)) if amount_match else None
    return amount, detect_currency(text) or default_currency


def parse_delivery_cost(text: str, default_currency: Optional[str] = None) -> Tuple[Optional[float], Optional[str]]:
    if not text:
        return None, default_currency

    lowered = text.lower()
    if any(word in lowered for word in ("gratis", "free", "darmowa")):
        return 0.0, detect_currency(text) or default_currency

    keyword_match = _DELIVERY_PATTERN.search(text)
    if keyword_match:
        amount = _to_float(keyword_match.group(2))
        return amount, detect_currency(text) or default_currency

    return parse_currency_amount(text, default_currency=default_currency)
