from __future__ import annotations

from typing import Iterable, Optional

from bs4 import BeautifulSoup
from bs4.element import Tag


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def select_first(soup: BeautifulSoup | Tag, selectors: Iterable[str]) -> Optional[Tag]:
    for selector in selectors:
        node = soup.select_one(selector)
        if node is not None:
            return node
    return None


def select_text(soup: BeautifulSoup | Tag, selectors: Iterable[str]) -> Optional[str]:
    node = select_first(soup, selectors)
    if node is None:
        return None
    text = node.get_text(" ", strip=True)
    return text or None


def first_attr(soup: BeautifulSoup | Tag, selectors: Iterable[str], attr: str) -> Optional[str]:
    node = select_first(soup, selectors)
    if node is None:
        return None
    value = node.get(attr)
    if not value:
        return None
    return str(value)


def stable_nodes(soup: BeautifulSoup, selectors: Iterable[str]) -> list[Tag]:
    for selector in selectors:
        nodes = soup.select(selector)
        if nodes:
            return list(nodes)
    return []
