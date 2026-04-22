from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Tuple

from common.http_client import HttpClient, HttpConfig, default_headers


@dataclass
class ScraperBase:
    env_prefix: str

    def __post_init__(self) -> None:
        self.headers = default_headers()
        self.http = HttpClient(config=self._http_config(), headers=self.headers)

    def _float_env(self, name: str, default: float) -> float:
        value = os.getenv(name)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def _int_env(self, name: str, default: int) -> int:
        value = os.getenv(name)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def _http_config(self) -> HttpConfig:
        prefix = self.env_prefix
        return HttpConfig(
            timeout=self._int_env(f"{prefix}_TIMEOUT", 15),
            retries=self._int_env(f"{prefix}_RETRIES", 2),
            backoff_seconds=self._float_env(f"{prefix}_BACKOFF_SECONDS", 1.0),
            rate_limit_seconds=self._float_env(f"{prefix}_RATE_LIMIT_SECONDS", 1.0),
            proxy=os.getenv(f"{prefix}_PROXY"),
        )

    def playwright_context_options(self) -> Dict[str, object]:
        return {
            "user_agent": self.headers.get("User-Agent"),
            "viewport": {"width": 1366, "height": 900},
            "locale": "pl-PL",
            "timezone_id": "Europe/Warsaw",
            "extra_http_headers": {"Accept-Language": self.headers.get("Accept-Language", "en-US,en;q=0.8")},
        }

    def playwright_launch_options(self) -> Tuple[Dict[str, object], Dict[str, object]]:
        return ({"headless": True}, self.playwright_context_options())
