from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Dict, Optional

import requests
from fake_useragent import UserAgent


DEFAULT_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def default_headers() -> Dict[str, str]:
    try:
        user_agent = UserAgent().random
    except Exception:
        user_agent = DEFAULT_UA
    return {
        "User-Agent": user_agent,
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7,it-IT;q=0.6",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


@dataclass
class HttpConfig:
    timeout: int = 15
    retries: int = 2
    backoff_seconds: float = 1.0
    rate_limit_seconds: float = 1.0
    proxy: Optional[str] = None


class HttpClient:
    def __init__(self, config: Optional[HttpConfig] = None, headers: Optional[Dict[str, str]] = None) -> None:
        self.config = config or HttpConfig()
        self.headers = headers or default_headers()
        self._last_request_ts = 0.0

    def _sleep_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_ts
        wait = max(0.0, self.config.rate_limit_seconds - elapsed)
        if wait > 0:
            time.sleep(wait)

    def get_text(self, url: str, params: Optional[Dict[str, str]] = None, extra_headers: Optional[Dict[str, str]] = None) -> Optional[str]:
        proxies = {"http": self.config.proxy, "https": self.config.proxy} if self.config.proxy else None
        headers = {**self.headers, **(extra_headers or {})}
        attempts = max(1, self.config.retries + 1)

        for attempt in range(attempts):
            self._sleep_for_rate_limit()
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.config.timeout,
                    proxies=proxies,
                )
                self._last_request_ts = time.monotonic()
                response.raise_for_status()
                return response.text
            except requests.RequestException:
                if attempt == attempts - 1:
                    return None
                time.sleep(self.config.backoff_seconds * (2 ** attempt) + random.uniform(0.0, 0.25))
        return None
