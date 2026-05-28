from __future__ import annotations

import time
from urllib.parse import urlparse

import httpx

from phases.common.config_loader import ScraperConfig, SchemeSource
from phases.p0_scrape.robots import is_allowed


class GrowwFetcher:
    """HTTP fetcher with allowlist, retries, and politeness delay."""

    def __init__(self, config: ScraperConfig) -> None:
        self._config = config
        self._last_request_at: float = 0.0

    def _validate_url(self, url: str) -> None:
        host = urlparse(url).netloc.lower()
        allowed = any(host == d or host.endswith(f".{d}") for d in self._config.allowed_domains)
        if not allowed:
            raise ValueError(f"URL not on allowlist: {url}")

    def _wait_politeness(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        delay = self._config.request_delay_seconds - elapsed
        if delay > 0:
            time.sleep(delay)

    def fetch(self, source: SchemeSource) -> tuple[str, str]:
        """Returns (final_url, html)."""
        self._validate_url(source.source_url)
        if not is_allowed(source.source_url, self._config.user_agent):
            raise PermissionError(f"robots.txt disallows fetch: {source.source_url}")
        timeout = httpx.Timeout(
            connect=self._config.timeout_connect_seconds,
            read=self._config.timeout_read_seconds,
            write=10.0,
            pool=10.0,
        )
        headers = {"User-Agent": self._config.user_agent, "Accept": "text/html,application/xhtml+xml"}

        last_error: Exception | None = None
        for attempt in range(self._config.max_retries):
            self._wait_politeness()
            try:
                with httpx.Client(
                    follow_redirects=True,
                    timeout=timeout,
                    headers=headers,
                ) as client:
                    response = client.get(source.source_url)
                    self._last_request_at = time.monotonic()
                    response.raise_for_status()
                    final_url = str(response.url)
                    self._validate_url(final_url)
                    return final_url, response.text
            except Exception as exc:
                last_error = exc
                if attempt < self._config.max_retries - 1:
                    backoff = self._config.retry_backoff_seconds * (2**attempt)
                    time.sleep(backoff)

        raise RuntimeError(
            f"Failed to fetch {source.source_url} after {self._config.max_retries} attempts: {last_error}"
        ) from last_error
