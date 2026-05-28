from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ScrapeStatus = Literal["success", "failed", "skipped"]


@dataclass
class SchemeScrapeResult:
    scheme_id: str
    source_url: str
    status: ScrapeStatus
    content_hash: str | None = None
    previous_hash: str | None = None
    hash_changed: bool = False
    facts_hash: str | None = None
    previous_facts_hash: str | None = None
    facts_hash_changed: bool = False
    facts_status: str | None = None
    error: str | None = None
    corpus_file: str | None = None


@dataclass
class ScrapeRunResult:
    scrape_run_id: str
    content_captured_at: str
    results: list[SchemeScrapeResult] = field(default_factory=list)
    corpus_changed: bool = False
    success_count: int = 0
    failed_count: int = 0

    def compute_summary(self) -> None:
        self.success_count = sum(1 for r in self.results if r.status == "success")
        self.failed_count = sum(1 for r in self.results if r.status == "failed")
        self.corpus_changed = any(
            r.hash_changed or r.facts_hash_changed for r in self.results
        )
