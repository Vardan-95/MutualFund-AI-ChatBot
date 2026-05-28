from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from phases.common.config_loader import SchemeSource, ScraperConfig
from phases.p0_scrape.fetcher import GrowwFetcher
from phases.p0_scrape.robots import is_allowed


class ParallelGrowwFetcher:
    """Bounded parallel fetcher (§4.2 max 2 concurrent)."""

    def __init__(self, config: ScraperConfig) -> None:
        self._config = config
        self._fetcher = GrowwFetcher(config)
        self._lock = Lock()

    def fetch_one(self, source: SchemeSource) -> tuple[SchemeSource, str, str]:
        if not is_allowed(source.source_url, self._config.user_agent):
            raise PermissionError(f"robots.txt disallows fetch: {source.source_url}")
        with self._lock:
            final_url, html = self._fetcher.fetch(source)
        return source, final_url, html

    def fetch_all(self, sources: list[SchemeSource]) -> dict[str, tuple[str, str]]:
        results: dict[str, tuple[str, str]] = {}
        workers = max(1, min(self._config.max_concurrent, len(sources)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self.fetch_one, s): s for s in sources}
            for future in as_completed(futures):
                source, final_url, html = future.result()
                results[source.scheme_id] = (final_url, html)
        return results
